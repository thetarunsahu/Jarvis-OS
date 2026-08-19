from __future__ import annotations

import os
import tempfile
import wave
from typing import Any, Callable, Protocol


StageCallback = Callable[[str], None]


class STTError(RuntimeError):
    """Base error for speech-to-text providers."""


class STTUnavailable(STTError):
    """Raised when a configured speech-to-text provider cannot run."""


class SpeechToTextProvider(Protocol):
    def transcribe_pcm(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        *,
        stage_callback: StageCallback | None = None,
    ) -> str:
        """Transcribe mono 16-bit PCM audio and return plain text."""


class FasterWhisperProvider:
    """Local multilingual STT backed by faster-whisper.

    The model is loaded lazily on first use and then kept resident for the
    lifetime of the provider. Defaults intentionally target CPU INT8 so JARVIS'
    local LLM can keep the laptop GPU for Ollama. Override with environment
    variables if a different profile is desired:

    JARVIS_STT_MODEL=small
    JARVIS_STT_DEVICE=cpu
    JARVIS_STT_COMPUTE=int8
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("JARVIS_STT_MODEL", "small")
        self.device = device or os.getenv("JARVIS_STT_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv(
            "JARVIS_STT_COMPUTE",
            "int8",
        )
        self._model_factory = model_factory
        self._model: Any | None = None
        self.last_language: str | None = None

    def _get_model(self, stage_callback: StageCallback | None = None) -> Any:
        if self._model is not None:
            return self._model

        _emit_stage(stage_callback, "loading_stt")

        try:
            if self._model_factory is None:
                from faster_whisper import WhisperModel

                factory = WhisperModel
            else:
                factory = self._model_factory

            self._model = factory(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as error:
            raise STTUnavailable(
                "Local speech recognition could not start. "
                "Install/update requirements and ensure the faster-whisper "
                f"model can load: {error}"
            ) from error

        return self._model

    def transcribe_pcm(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        *,
        stage_callback: StageCallback | None = None,
    ) -> str:
        if not audio_bytes:
            return ""

        model = self._get_model(stage_callback)
        temp_path = _write_temp_wav(audio_bytes, sample_rate)

        try:
            try:
                segments, info = model.transcribe(
                    temp_path,
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 350},
                    condition_on_previous_text=False,
                )
                items = list(segments)
            except Exception as error:
                raise STTError(f"Local transcription failed: {error}") from error

            language = getattr(info, "language", None)
            self.last_language = str(language) if language else None
            return " ".join(
                str(getattr(segment, "text", "")).strip()
                for segment in items
                if str(getattr(segment, "text", "")).strip()
            ).strip()
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass


class GoogleSpeechProvider:
    """Compatibility provider for tests or explicit online fallback usage."""

    def __init__(self, recognizer: Any | None = None) -> None:
        try:
            import speech_recognition as sr
        except Exception as error:
            raise STTUnavailable(
                f"SpeechRecognition is unavailable: {error}"
            ) from error

        self._sr = sr
        self.recognizer = recognizer or sr.Recognizer()

    def transcribe_pcm(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        *,
        stage_callback: StageCallback | None = None,
    ) -> str:
        del stage_callback
        if not audio_bytes:
            return ""

        temp_path = _write_temp_wav(audio_bytes, sample_rate)
        try:
            with self._sr.AudioFile(temp_path) as source:
                audio = self.recognizer.record(source)

            try:
                text = self.recognizer.recognize_google(audio)
            except self._sr.UnknownValueError:
                return ""
            except self._sr.RequestError as error:
                raise STTUnavailable(
                    f"Online speech recognition failed: {error}"
                ) from error

            return str(text).strip()
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _write_temp_wav(audio_bytes: bytes, sample_rate: int) -> str:
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    with wave.open(temp_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(int(sample_rate))
        wav_file.writeframes(audio_bytes)

    return temp_path


def _emit_stage(callback: StageCallback | None, stage: str) -> None:
    if callback is None:
        return
    try:
        callback(stage)
    except Exception:
        pass
