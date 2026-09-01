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

    JARVIS intentionally accepts only English and Hindi by default. Hinglish is
    naturally covered because Whisper generally classifies mixed Hindi/English
    speech as one of those two languages. Low-confidence language detections and
    low-confidence speech segments are rejected instead of being passed to the
    assistant as commands.

    Environment overrides:
      JARVIS_STT_MODEL=small
      JARVIS_STT_DEVICE=cpu
      JARVIS_STT_COMPUTE=int8
      JARVIS_STT_LANGUAGES=en,hi
      JARVIS_STT_MIN_LANGUAGE_PROB=0.35
      JARVIS_STT_MIN_AVG_LOGPROB=-1.15
      JARVIS_STT_MAX_NO_SPEECH_PROB=0.60
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        model_factory: Callable[..., Any] | None = None,
        allowed_languages: set[str] | None = None,
        min_language_probability: float | None = None,
        min_avg_logprob: float | None = None,
        max_no_speech_probability: float | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("JARVIS_STT_MODEL", "small")
        self.device = device or os.getenv("JARVIS_STT_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv(
            "JARVIS_STT_COMPUTE",
            "int8",
        )
        configured_languages = os.getenv("JARVIS_STT_LANGUAGES", "en,hi")
        self.allowed_languages = allowed_languages or {
            item.strip().lower()
            for item in configured_languages.split(",")
            if item.strip()
        }
        self.min_language_probability = float(
            min_language_probability
            if min_language_probability is not None
            else os.getenv("JARVIS_STT_MIN_LANGUAGE_PROB", "0.35")
        )
        self.min_avg_logprob = float(
            min_avg_logprob
            if min_avg_logprob is not None
            else os.getenv("JARVIS_STT_MIN_AVG_LOGPROB", "-1.15")
        )
        self.max_no_speech_probability = float(
            max_no_speech_probability
            if max_no_speech_probability is not None
            else os.getenv("JARVIS_STT_MAX_NO_SPEECH_PROB", "0.60")
        )
        self._model_factory = model_factory
        self._model: Any | None = None
        self.last_language: str | None = None
        self.last_language_probability: float | None = None
        self.last_rejection: str | None = None

        if not self.allowed_languages:
            raise ValueError("allowed_languages cannot be empty")
        if not 0.0 <= self.min_language_probability <= 1.0:
            raise ValueError("min_language_probability must be between 0 and 1")
        if not 0.0 <= self.max_no_speech_probability <= 1.0:
            raise ValueError("max_no_speech_probability must be between 0 and 1")

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

        self.last_rejection = None
        model = self._get_model(stage_callback)
        temp_path = _write_temp_wav(audio_bytes, sample_rate)

        try:
            try:
                segments, info = model.transcribe(
                    temp_path,
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 350,
                        "speech_pad_ms": 120,
                    },
                    condition_on_previous_text=False,
                )
                items = list(segments)
            except Exception as error:
                raise STTError(f"Local transcription failed: {error}") from error

            language = getattr(info, "language", None)
            language_probability = getattr(info, "language_probability", None)
            self.last_language = str(language).lower() if language else None
            try:
                self.last_language_probability = (
                    float(language_probability)
                    if language_probability is not None
                    else None
                )
            except (TypeError, ValueError):
                self.last_language_probability = None

            if (
                self.last_language is not None
                and self.last_language not in self.allowed_languages
            ):
                self.last_rejection = f"unsupported_language:{self.last_language}"
                return ""

            if (
                self.last_language_probability is not None
                and self.last_language_probability < self.min_language_probability
            ):
                self.last_rejection = "low_language_confidence"
                return ""

            accepted: list[str] = []
            for segment in items:
                text = str(getattr(segment, "text", "")).strip()
                if not text:
                    continue

                if not self._segment_is_reliable(segment):
                    continue

                accepted.append(text)

            transcript = " ".join(accepted).strip()
            if not transcript:
                self.last_rejection = "low_speech_confidence"
                return ""

            if not any(character.isalnum() for character in transcript):
                self.last_rejection = "non_speech_text"
                return ""

            return transcript
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _segment_is_reliable(self, segment: Any) -> bool:
        avg_logprob = getattr(segment, "avg_logprob", None)
        no_speech_prob = getattr(segment, "no_speech_prob", None)

        try:
            if (
                avg_logprob is not None
                and float(avg_logprob) < self.min_avg_logprob
            ):
                return False
        except (TypeError, ValueError):
            pass

        try:
            if (
                no_speech_prob is not None
                and float(no_speech_prob) > self.max_no_speech_probability
            ):
                return False
        except (TypeError, ValueError):
            pass

        return True


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
