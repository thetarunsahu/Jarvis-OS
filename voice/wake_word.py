from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import sounddevice as sd


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

    Audio remains local. The detector uses 16 kHz mono PCM frames and ONNX on
    Windows. The model is downloaded lazily the first time it is needed and is
    then kept resident for the lifetime of this detector instance.

    Environment overrides:
      JARVIS_WAKE_WORD=hey_jarvis
      JARVIS_WAKE_THRESHOLD=0.62
      JARVIS_WAKE_VAD_THRESHOLD=0.45
    """

    def __init__(
        self,
        model_name: str | None = None,
        threshold: float | None = None,
        vad_threshold: float | None = None,
        sample_rate: int = 16000,
        chunk_samples: int = 1280,
        model_factory: ModelFactory | None = None,
        stream_factory: StreamFactory | None = None,
    ) -> None:
        self.model_name = (
            model_name or os.getenv("JARVIS_WAKE_WORD", "hey_jarvis")
        ).strip()
        self.threshold = float(
            threshold
            if threshold is not None
            else os.getenv("JARVIS_WAKE_THRESHOLD", "0.62")
        )
        self.vad_threshold = float(
            vad_threshold
            if vad_threshold is not None
            else os.getenv("JARVIS_WAKE_VAD_THRESHOLD", "0.45")
        )
        self.sample_rate = int(sample_rate)
        self.chunk_samples = int(chunk_samples)
        self._model_factory = model_factory
        self._stream_factory = stream_factory or sd.RawInputStream
        self._model: Any | None = None

        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if not 0.0 <= self.vad_threshold <= 1.0:
            raise ValueError("vad_threshold must be between 0 and 1")
        if self.sample_rate != 16000:
            raise ValueError("openWakeWord requires a 16000 Hz sample rate")
        if self.chunk_samples <= 0 or self.chunk_samples % 1280 != 0:
            raise ValueError("chunk_samples must be a positive multiple of 1280")

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

        try:
            with self._stream_factory(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_samples,
            ) as stream:
                while not stop_event.is_set():
                    raw = stream.read(self.chunk_samples)
                    if isinstance(raw, tuple):
                        raw = raw[0]

                    frame = np.frombuffer(bytes(raw), dtype=np.int16)
                    if frame.size == 0:
                        continue

                    try:
                        scores = model.predict(frame)
                    except Exception as error:
                        raise WakeWordError(
                            f"Wake-word inference failed: {error}"
                        ) from error

                    score = self._extract_score(scores)
                    if score >= self.threshold:
                        try:
                            reset = getattr(model, "reset", None)
                            if callable(reset):
                                reset()
                        finally:
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
        best = 0.0
        for name, value in scores.items():
            try:
                score = float(value)
            except (TypeError, ValueError):
                continue

            key = str(name).lower().replace("-", "_").replace(" ", "_")
            if target in key or key in target or "jarvis" in key:
                best = max(best, score)

        if best > 0.0:
            return best

        numeric_scores: list[float] = []
        for value in scores.values():
            try:
                numeric_scores.append(float(value))
            except (TypeError, ValueError):
                pass
        return max(numeric_scores, default=0.0)

    @staticmethod
    def _emit_stage(callback: StageCallback | None, stage: str) -> None:
        if callback is None:
            return
        try:
            callback(stage)
        except Exception:
            pass
