from __future__ import annotations

import os
import tempfile
import wave
from typing import Any, Callable

import pyttsx3
import sounddevice as sd
import speech_recognition as sr


Recorder = Callable[..., Any]
WaitForRecording = Callable[[], None]
EngineFactory = Callable[[], Any]


class VoiceError(RuntimeError):
    """Base error for microphone, recognition, and speech failures."""


class VoiceRecognitionUnavailable(VoiceError):
    """Raised when the configured speech-recognition service is unavailable."""


class VoiceManager:
    """Blocking voice primitives used by background workers.

    This class intentionally contains no Qt code. The desktop interface is
    responsible for calling ``listen`` and ``speak`` off the GUI thread.
    pyttsx3 is initialised lazily inside ``speak`` so its Windows COM objects
    are created on the same worker thread that uses them.
    """

    def __init__(
        self,
        recognizer: Any | None = None,
        recorder: Recorder | None = None,
        wait_for_recording: WaitForRecording | None = None,
        engine_factory: EngineFactory | None = None,
        rate: int = 175,
        volume: float = 1.0,
    ) -> None:
        self.recognizer = recognizer or sr.Recognizer()
        self._recorder = recorder or sd.rec
        self._wait_for_recording = wait_for_recording or sd.wait
        self._engine_factory = engine_factory or pyttsx3.init
        self.rate = int(rate)
        self.volume = max(0.0, min(1.0, float(volume)))

    def listen(self, duration: float = 5.0, sample_rate: int = 16000) -> str:
        """Capture microphone audio and return recognised text.

        The current recogniser is Google's SpeechRecognition backend, so STT
        requires internet access. Returning an empty string means speech was
        captured but could not be understood.
        """
        duration = float(duration)
        sample_rate = int(sample_rate)

        if duration <= 0:
            raise ValueError("duration must be greater than zero")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")

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

        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            try:
                audio_bytes = recording.tobytes()
            except Exception as error:
                raise VoiceError(f"Audio buffer conversion failed: {error}") from error

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
