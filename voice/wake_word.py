from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import sounddevice as sd

from voice.audio_service import AudioInputService, get_audio_input_service


StageCallback = Callable[[str], None]
ModelFactory = Callable[[], Any]
StreamFactory = Callable[..., Any]


class WakeWordError(RuntimeError):
    """Raised when the always-on wake-word listener cannot run."""


@dataclass(frozen=True)
class WakeDetection:
    model_name: str
    score: float


class WakeWordDetector:
    """Low-latency local wake-word detection using openWakeWord.

    Production uses the process-wide ``AudioInputService`` so wake detection no
    longer owns a second microphone stream. Tests can still inject a legacy
    stream factory to exercise the detector in isolation.

    Environment overrides:
      JARVIS_WAKE_WORD=hey_jarvis
      JARVIS_WAKE_THRESHOLD=0.70
      JARVIS_WAKE_VAD_THRESHOLD=0.55
      JARVIS_WAKE_REQUIRED_HITS=2
    """

    def __init__(
        self,
        model_name: str | None = None,
        threshold: float | None = None,
        vad_threshold: float | None = None,
        required_hits: int | None = None,
        sample_rate: int = 16000,
        chunk_samples: int = 1280,
        model_factory: ModelFactory | None = None,
        stream_factory: StreamFactory | None = None,
        audio_service: AudioInputService | None = None,
    ) -> None:
        self.model_name = (
            model_name or os.getenv("JARVIS_WAKE_WORD", "hey_jarvis")
        ).strip()
        self.threshold = float(
            threshold
            if threshold is not None
            else os.getenv("JARVIS_WAKE_THRESHOLD", "0.70")
        )
        self.vad_threshold = float(
            vad_threshold
            if vad_threshold is not None
            else os.getenv("JARVIS_WAKE_VAD_THRESHOLD", "0.55")
        )
        self.required_hits = int(
            required_hits
            if required_hits is not None
            else os.getenv("JARVIS_WAKE_REQUIRED_HITS", "2")
        )
        self.sample_rate = int(sample_rate)
        self.chunk_samples = int(chunk_samples)
        self._model_factory = model_factory
        self._stream_factory = stream_factory
        self._audio_service = (
            audio_service
            if audio_service is not None
            else (None if stream_factory is not None else get_audio_input_service())
        )
        self._model: Any | None = None

        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if not 0.0 <= self.vad_threshold <= 1.0:
            raise ValueError("vad_threshold must be between 0 and 1")
        if self.required_hits < 1 or self.required_hits > 5:
            raise ValueError("required_hits must be between 1 and 5")
        if self.sample_rate != 16000:
            raise ValueError("openWakeWord requires a 16000 Hz sample rate")
        if self.chunk_samples <= 0 or self.chunk_samples % 1280 != 0:
            raise ValueError("chunk_samples must be a positive multiple of 1280")
        if (
            self._audio_service is not None
            and self._audio_service.sample_rate != self.sample_rate
        ):
            raise ValueError("wake detector and audio service sample rates must match")

    def wait_for_wake_word(
        self,
        stop_event: threading.Event,
        *,
        stage_callback: StageCallback | None = None,
    ) -> WakeDetection | None:
        """Block until the wake phrase is heard or ``stop_event`` is set."""

        model = self._get_model(stage_callback)
        if stop_event.is_set():
            return None

        self._emit_stage(stage_callback, "wake_armed")

        if self._audio_service is not None:
            return self._wait_from_audio_service(
                model,
                stop_event,
                stage_callback=stage_callback,
            )

        return self._wait_from_legacy_stream(
            model,
            stop_event,
            stage_callback=stage_callback,
        )

    def _wait_from_audio_service(
        self,
        model: Any,
        stop_event: threading.Event,
        *,
        stage_callback: StageCallback | None,
    ) -> WakeDetection | None:
        service = self._audio_service
        if service is None:
            return None

        try:
            cursor = service.latest_sequence()
        except Exception as error:
            raise WakeWordError(f"Wake-word microphone failed: {error}") from error

        pending = bytearray()
        required_bytes = self.chunk_samples * 2
        strong_hits = 0
        chunk_end_sequence = cursor

        while not stop_event.is_set():
            try:
                frame = service.read_after(cursor, timeout=0.25)
            except Exception as error:
                raise WakeWordError(f"Wake-word microphone failed: {error}") from error

            if frame is None:
                continue

            cursor = frame.sequence
            chunk_end_sequence = frame.sequence
            pending.extend(frame.pcm)

            while len(pending) >= required_bytes and not stop_event.is_set():
                raw = bytes(pending[:required_bytes])
                del pending[:required_bytes]

                detection = self._score_chunk(
                    model,
                    raw,
                    strong_hits=strong_hits,
                )
                strong_hits = detection[0]
                score = detection[1]

                if strong_hits >= self.required_hits:
                    service.mark_wake_detected(chunk_end_sequence)
                    self._reset_model(model)
                    self._emit_stage(stage_callback, "wake_detected")
                    return WakeDetection(
                        model_name=self.model_name,
                        score=score,
                    )

        return None

    def _wait_from_legacy_stream(
        self,
        model: Any,
        stop_event: threading.Event,
        *,
        stage_callback: StageCallback | None,
    ) -> WakeDetection | None:
        stream_factory = self._stream_factory or sd.RawInputStream
        strong_hits = 0

        try:
            with stream_factory(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_samples,
            ) as stream:
                while not stop_event.is_set():
                    raw = stream.read(self.chunk_samples)
                    if isinstance(raw, tuple):
                        raw = raw[0]

                    strong_hits, score = self._score_chunk(
                        model,
                        bytes(raw),
                        strong_hits=strong_hits,
                    )

                    if strong_hits >= self.required_hits:
                        self._reset_model(model)
                        self._emit_stage(stage_callback, "wake_detected")
                        return WakeDetection(
                            model_name=self.model_name,
                            score=score,
                        )
        except WakeWordError:
            raise
        except Exception as error:
            raise WakeWordError(f"Wake-word microphone failed: {error}") from error

        return None

    def _score_chunk(
        self,
        model: Any,
        raw: bytes,
        *,
        strong_hits: int,
    ) -> tuple[int, float]:
        frame = np.frombuffer(raw, dtype=np.int16)
        if frame.size == 0:
            return 0, 0.0

        try:
            scores = model.predict(frame)
        except Exception as error:
            raise WakeWordError(f"Wake-word inference failed: {error}") from error

        score = self._extract_score(scores)
        if score >= self.threshold:
            strong_hits += 1
        else:
            strong_hits = 0
        return strong_hits, score

    @staticmethod
    def _reset_model(model: Any) -> None:
        reset = getattr(model, "reset", None)
        if callable(reset):
            reset()

    def _get_model(self, stage_callback: StageCallback | None = None) -> Any:
        if self._model is not None:
            return self._model

        self._emit_stage(stage_callback, "wake_loading")

        try:
            if self._model_factory is not None:
                self._model = self._model_factory()
                return self._model

            import openwakeword
            from openwakeword.model import Model
            from openwakeword.utils import download_models

            download_models(model_names=[self.model_name])

            model_ref = self.model_name
            catalog = getattr(openwakeword, "MODELS", {})
            model_info = catalog.get(self.model_name) if isinstance(catalog, dict) else None
            if isinstance(model_info, dict):
                model_path = str(model_info.get("model_path", "")).strip()
                if model_path:
                    model_ref = model_path.replace(".tflite", ".onnx")

            self._model = Model(
                wakeword_models=[model_ref],
                inference_framework="onnx",
                vad_threshold=self.vad_threshold,
            )
            return self._model
        except Exception as error:
            raise WakeWordError(
                "Local wake-word detection could not start. "
                "Install/update requirements and allow the first-time model "
                f"download: {error}"
            ) from error

    def _extract_score(self, scores: Any) -> float:
        if not isinstance(scores, dict) or not scores:
            return 0.0

        target = self.model_name.lower().replace("-", "_").replace(" ", "_")
        matched_scores: list[float] = []
        numeric_scores: list[float] = []

        for name, value in scores.items():
            try:
                score = float(value)
            except (TypeError, ValueError):
                continue

            numeric_scores.append(score)
            key = str(name).lower().replace("-", "_").replace(" ", "_")
            if target in key or key in target:
                matched_scores.append(score)

        if matched_scores:
            return max(matched_scores)

        if self._model_factory is not None and len(numeric_scores) == 1:
            return numeric_scores[0]
        return 0.0

    @staticmethod
    def _emit_stage(callback: StageCallback | None, stage: str) -> None:
        if callback is None:
            return
        try:
            callback(stage)
        except Exception:
            pass
