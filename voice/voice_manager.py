from __future__ import annotations

import threading
import time
from array import array
from collections import deque
from statistics import median
from typing import Any, Callable

import pyttsx3
import sounddevice as sd

from voice.stt_providers import (
    FasterWhisperProvider,
    GoogleSpeechProvider,
    SpeechToTextProvider,
    STTError,
    STTUnavailable,
)


Recorder = Callable[..., Any]
WaitForRecording = Callable[[], None]
EngineFactory = Callable[[], Any]
StreamFactory = Callable[..., Any]
StageCallback = Callable[[str], None]


class VoiceError(RuntimeError):
    """Base error for microphone, recognition, and speech failures."""


class VoiceRecognitionUnavailable(VoiceError):
    """Raised when the configured speech-recognition engine is unavailable."""


class VoiceManager:
    """Blocking voice primitives used by background workers.

    The real microphone path uses adaptive speech gating before STT. A short
    ambient-noise estimate, consecutive speech frames, minimum voiced duration,
    and pre-roll are used together so fan noise or one loud click does not become
    a command while the beginning of a real utterance is preserved.
    """

    def __init__(
        self,
        recognizer: Any | None = None,
        stt_provider: SpeechToTextProvider | None = None,
        recorder: Recorder | None = None,
        wait_for_recording: WaitForRecording | None = None,
        engine_factory: EngineFactory | None = None,
        stream_factory: StreamFactory | None = None,
        rate: int = 175,
        volume: float = 1.0,
    ) -> None:
        if stt_provider is not None:
            self.stt_provider = stt_provider
        elif recognizer is not None:
            self.stt_provider = GoogleSpeechProvider(recognizer=recognizer)
        else:
            self.stt_provider = FasterWhisperProvider()

        self._adaptive_listen = recorder is None
        self._recorder = recorder or sd.rec
        self._wait_for_recording = wait_for_recording or sd.wait
        self._engine_factory = engine_factory or pyttsx3.init
        self._stream_factory = stream_factory or sd.RawInputStream
        self.rate = int(rate)
        self.volume = max(0.0, min(1.0, float(volume)))

        self.last_noise_floor: int | None = None
        self.last_energy_threshold: int | None = None
        self.last_capture_rejection: str | None = None

    def listen(
        self,
        duration: float = 8.0,
        sample_rate: int = 16000,
        stage_callback: StageCallback | None = None,
    ) -> str:
        """Capture microphone audio and return recognised text."""
        duration = float(duration)
        sample_rate = int(sample_rate)

        if duration <= 0:
            raise ValueError("duration must be greater than zero")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")

        self.last_capture_rejection = None
        self._emit_stage(stage_callback, "listening")

        if self._adaptive_listen:
            return self.listen_until_silence(
                sample_rate=sample_rate,
                max_duration=duration,
                stage_callback=stage_callback,
            )

        try:
            recording = self._recorder(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
            self._wait_for_recording()
        except Exception as error:
            raise VoiceError(f"Microphone capture failed: {error}") from error

        try:
            audio_bytes = recording.tobytes()
        except Exception as error:
            raise VoiceError(f"Audio buffer conversion failed: {error}") from error

        self._emit_stage(stage_callback, "transcribing")
        return self._recognize_pcm(audio_bytes, sample_rate, stage_callback)

    def listen_until_silence(
        self,
        sample_rate: int = 16000,
        start_timeout: float = 2.5,
        max_duration: float = 8.0,
        silence_duration: float = 0.65,
        energy_threshold: int = 450,
        noise_multiplier: float = 2.2,
        speech_start_frames: int = 3,
        minimum_voice_frames: int = 5,
        warmup_frames: int = 4,
        pre_roll_frames: int = 6,
        stage_callback: StageCallback | None = None,
    ) -> str:
        """Listen until speech ends while rejecting short/noisy false starts.

        Audio is processed in ~50 ms frames. The first few frames estimate the
        ambient level. Speech must then remain above an adaptive threshold for
        several consecutive frames before capture begins. This avoids sending
        random room noise to Whisper and then to the language model.
        """
        sample_rate = int(sample_rate)
        start_timeout = float(start_timeout)
        max_duration = float(max_duration)
        silence_duration = float(silence_duration)
        energy_threshold = int(energy_threshold)
        noise_multiplier = float(noise_multiplier)
        speech_start_frames = int(speech_start_frames)
        minimum_voice_frames = int(minimum_voice_frames)
        warmup_frames = int(warmup_frames)
        pre_roll_frames = int(pre_roll_frames)

        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")
        if start_timeout <= 0:
            raise ValueError("start_timeout must be greater than zero")
        if max_duration <= 0:
            raise ValueError("max_duration must be greater than zero")
        if silence_duration <= 0:
            raise ValueError("silence_duration must be greater than zero")
        if energy_threshold < 0:
            raise ValueError("energy_threshold must not be negative")
        if noise_multiplier < 1.0:
            raise ValueError("noise_multiplier must be at least 1")
        if speech_start_frames < 1:
            raise ValueError("speech_start_frames must be positive")
        if minimum_voice_frames < speech_start_frames:
            raise ValueError(
                "minimum_voice_frames must be >= speech_start_frames"
            )
        if warmup_frames < 0 or pre_roll_frames < 1:
            raise ValueError("invalid warmup/pre-roll frame configuration")

        chunks: list[bytes] = []
        pre_roll: deque[bytes] = deque(maxlen=pre_roll_frames)
        ambient_levels: deque[int] = deque(maxlen=24)
        done = threading.Event()
        started_at = time.monotonic()
        speech_started = False
        last_voice_at: float | None = None
        candidate_voice_frames = 0
        voiced_frames = 0
        frame_count = 0

        def callback(indata, frames, time_info, status) -> None:
            del frames, time_info, status
            nonlocal speech_started
            nonlocal last_voice_at
            nonlocal candidate_voice_frames
            nonlocal voiced_frames
            nonlocal frame_count

            now = time.monotonic()
            chunk = bytes(indata)
            rms = self._pcm_rms(chunk)
            frame_count += 1
            pre_roll.append(chunk)

            if ambient_levels:
                noise_floor = int(median(ambient_levels))
                adaptive_threshold = max(
                    energy_threshold,
                    int(noise_floor * noise_multiplier) + 80,
                )
            else:
                noise_floor = 0
                adaptive_threshold = energy_threshold

            self.last_noise_floor = noise_floor
            self.last_energy_threshold = adaptive_threshold

            if not speech_started:
                if frame_count <= warmup_frames:
                    ambient_levels.append(rms)
                    candidate_voice_frames = 0
                elif rms >= adaptive_threshold:
                    candidate_voice_frames += 1
                    if candidate_voice_frames >= speech_start_frames:
                        speech_started = True
                        voiced_frames = candidate_voice_frames
                        last_voice_at = now
                        chunks.extend(pre_roll)
                else:
                    candidate_voice_frames = 0
                    # Only learn from quiet frames. This prevents a spoken word
                    # from raising the ambient baseline before capture starts.
                    if rms <= max(energy_threshold, int(adaptive_threshold * 0.8)):
                        ambient_levels.append(rms)

                if not speech_started and now - started_at >= start_timeout:
                    done.set()
            else:
                chunks.append(chunk)
                release_threshold = max(
                    energy_threshold,
                    int(adaptive_threshold * 0.70),
                )
                if rms >= release_threshold:
                    voiced_frames += 1
                    last_voice_at = now

                if (
                    last_voice_at is not None
                    and now - last_voice_at >= silence_duration
                ):
                    done.set()

            if now - started_at >= max_duration:
                done.set()

        blocksize = max(256, int(sample_rate * 0.05))

        try:
            with self._stream_factory(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=blocksize,
                callback=callback,
            ):
                done.wait(timeout=max_duration + 1.0)
        except Exception as error:
            raise VoiceError(f"Microphone capture failed: {error}") from error

        if not speech_started:
            self.last_capture_rejection = "no_sustained_speech"
            return ""

        if voiced_frames < minimum_voice_frames:
            self.last_capture_rejection = "speech_too_short"
            return ""

        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            self.last_capture_rejection = "empty_audio"
            return ""

        self._emit_stage(stage_callback, "transcribing")
        transcript = self._recognize_pcm(
            audio_bytes,
            sample_rate,
            stage_callback,
        )
        if not transcript:
            self.last_capture_rejection = (
                getattr(self.stt_provider, "last_rejection", None)
                or "stt_rejected"
            )
        return transcript

    def _recognize_pcm(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        stage_callback: StageCallback | None = None,
    ) -> str:
        try:
            return self.stt_provider.transcribe_pcm(
                audio_bytes,
                sample_rate,
                stage_callback=stage_callback,
            ).strip()
        except STTUnavailable as error:
            raise VoiceRecognitionUnavailable(str(error)) from error
        except STTError as error:
            raise VoiceError(str(error)) from error
        except Exception as error:
            raise VoiceError(f"Speech recognition failed: {error}") from error

    @staticmethod
    def _emit_stage(
        callback: StageCallback | None,
        stage: str,
    ) -> None:
        if callback is None:
            return
        try:
            callback(stage)
        except Exception:
            pass

    @staticmethod
    def _pcm_rms(audio_bytes: bytes) -> int:
        if not audio_bytes:
            return 0

        samples = array("h")
        samples.frombytes(audio_bytes)
        if not samples:
            return 0

        total = sum(sample * sample for sample in samples)
        return int((total / len(samples)) ** 0.5)

    def speak(self, text: str) -> None:
        """Speak text using the local Windows TTS engine."""
        message = str(text).strip()
        if not message:
            return

        try:
            engine = self._engine_factory()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            engine.say(message)
            engine.runAndWait()
        except Exception as error:
            raise VoiceError(f"Text-to-speech failed: {error}") from error
        finally:
            if "engine" in locals():
                try:
                    engine.stop()
                except Exception:
                    pass
