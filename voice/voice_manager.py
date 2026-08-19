from __future__ import annotations

import os
import tempfile
import threading
import time
import wave
from array import array
from typing import Any, Callable

import pyttsx3
import sounddevice as sd
import speech_recognition as sr


Recorder = Callable[..., Any]
WaitForRecording = Callable[[], None]
EngineFactory = Callable[[], Any]
StreamFactory = Callable[..., Any]
StageCallback = Callable[[str], None]


class VoiceError(RuntimeError):
    """Base error for microphone, recognition, and speech failures."""


class VoiceRecognitionUnavailable(VoiceError):
    """Raised when the configured speech-recognition service is unavailable."""


class VoiceManager:
    """Blocking voice primitives used by background workers.

    This class intentionally contains no Qt code. The desktop interface is
    responsible for calling ``listen`` / ``listen_until_silence`` and ``speak``
    off the GUI thread. pyttsx3 is initialised lazily inside ``speak`` so its
    Windows COM objects are created on the same worker thread that uses them.
    """

    def __init__(
        self,
        recognizer: Any | None = None,
        recorder: Recorder | None = None,
        wait_for_recording: WaitForRecording | None = None,
        engine_factory: EngineFactory | None = None,
        stream_factory: StreamFactory | None = None,
        rate: int = 175,
        volume: float = 1.0,
    ) -> None:
        self.recognizer = recognizer or sr.Recognizer()
        self._adaptive_listen = recorder is None
        self._recorder = recorder or sd.rec
        self._wait_for_recording = wait_for_recording or sd.wait
        self._engine_factory = engine_factory or pyttsx3.init
        self._stream_factory = stream_factory or sd.RawInputStream
        self.rate = int(rate)
        self.volume = max(0.0, min(1.0, float(volume)))

    def listen(
        self,
        duration: float = 8.0,
        sample_rate: int = 16000,
        stage_callback: StageCallback | None = None,
    ) -> str:
        """Capture microphone audio and return recognised text.

        With the real microphone this is adaptive: recording ends shortly after
        speech stops, while ``duration`` acts as a safety cap. Injected recorders
        keep the fixed-duration path so tests and alternate callers remain stable.
        """
        duration = float(duration)
        sample_rate = int(sample_rate)

        if duration <= 0:
            raise ValueError("duration must be greater than zero")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")

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
        return self._recognize_pcm(audio_bytes, sample_rate)

    def listen_until_silence(
        self,
        sample_rate: int = 16000,
        start_timeout: float = 2.5,
        max_duration: float = 8.0,
        silence_duration: float = 0.5,
        energy_threshold: int = 300,
        stage_callback: StageCallback | None = None,
    ) -> str:
        """Listen until the user stops speaking instead of waiting a fixed time.

        Recording starts immediately. If speech is detected, capture stops after
        roughly ``silence_duration`` seconds of silence. If no speech is detected,
        the call returns after ``start_timeout`` seconds. ``max_duration`` is a
        safety cap for unusually long or noisy input.
        """
        sample_rate = int(sample_rate)
        start_timeout = float(start_timeout)
        max_duration = float(max_duration)
        silence_duration = float(silence_duration)
        energy_threshold = int(energy_threshold)

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

        chunks: list[bytes] = []
        done = threading.Event()
        started_at = time.monotonic()
        speech_started = False
        last_voice_at: float | None = None

        def callback(indata, frames, time_info, status) -> None:
            del frames, time_info, status
            nonlocal speech_started, last_voice_at

            now = time.monotonic()
            chunk = bytes(indata)
            rms = self._pcm_rms(chunk)

            if rms >= energy_threshold:
                speech_started = True
                last_voice_at = now

            if speech_started:
                chunks.append(chunk)
                if (
                    last_voice_at is not None
                    and now - last_voice_at >= silence_duration
                ):
                    done.set()
            elif now - started_at >= start_timeout:
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

        if not chunks:
            return ""

        self._emit_stage(stage_callback, "transcribing")
        return self._recognize_pcm(b"".join(chunks), sample_rate)

    def _recognize_pcm(self, audio_bytes: bytes, sample_rate: int) -> str:
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_bytes)

            with sr.AudioFile(temp_path) as source:
                audio = self.recognizer.record(source)

            try:
                text = self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as error:
                raise VoiceRecognitionUnavailable(
                    f"Speech recognition service failed: {error}"
                ) from error

            return str(text).strip()
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

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
