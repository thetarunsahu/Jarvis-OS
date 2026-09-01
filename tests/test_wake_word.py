import threading

import numpy as np
import pytest

from voice.wake_word import WakeWordDetector


class FakeModel:
    def __init__(self, scores):
        self.scores = iter(scores)
        self.reset_called = False

    def predict(self, frame):
        assert isinstance(frame, np.ndarray)
        assert frame.dtype == np.int16
        return next(self.scores)

    def reset(self):
        self.reset_called = True


class FakeStream:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.opened = False

    def __enter__(self):
        self.opened = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.opened = False

    def read(self, frames):
        chunk = next(self.chunks)
        assert len(chunk) == frames * 2
        return chunk, False


def pcm_chunk(samples=1280):
    return (np.ones(samples, dtype=np.int16) * 100).tobytes()


def test_wake_detector_requires_repeated_high_scores():
    model = FakeModel([
        {"hey_jarvis": 0.20},
        {"hey_jarvis": 0.81},
        {"hey_jarvis": 0.85},
    ])
    stream = FakeStream([pcm_chunk(), pcm_chunk(), pcm_chunk()])
    stages = []

    detector = WakeWordDetector(
        threshold=0.60,
        required_hits=2,
        model_factory=lambda: model,
        stream_factory=lambda **kwargs: stream,
    )

    result = detector.wait_for_wake_word(
        threading.Event(),
        stage_callback=stages.append,
    )

    assert result is not None
    assert result.model_name == "hey_jarvis"
    assert result.score == pytest.approx(0.85)
    assert model.reset_called is True
    assert stages == ["wake_loading", "wake_armed", "wake_detected"]


def test_wake_detector_resets_confirmation_after_a_miss():
    model = FakeModel([
        {"hey_jarvis": 0.71},
        {"hey_jarvis": 0.72},
        {"hey_jarvis": 0.10},
        {"hey_jarvis": 0.73},
        {"hey_jarvis": 0.74},
        {"hey_jarvis": 0.75},
    ])
    stream = FakeStream([pcm_chunk() for _ in range(6)])

    detector = WakeWordDetector(
        threshold=0.70,
        required_hits=3,
        model_factory=lambda: model,
        stream_factory=lambda **kwargs: stream,
    )

    result = detector.wait_for_wake_word(threading.Event())

    assert result is not None
    assert result.score == pytest.approx(0.75)


def test_extract_score_refuses_ambiguous_unknown_models():
    detector = WakeWordDetector(
        model_factory=lambda: FakeModel([]),
        stream_factory=lambda **kwargs: None,
    )

    assert detector._extract_score({"alexa": 0.99, "computer": 0.95}) == 0.0


def test_extract_score_refuses_unknown_single_production_model():
    detector = WakeWordDetector()

    assert detector._extract_score({"alexa": 0.99}) == 0.0


def test_wake_detector_returns_none_when_already_stopped():
    model = FakeModel([])
    stream_calls = []
    stop_event = threading.Event()
    stop_event.set()

    detector = WakeWordDetector(
        model_factory=lambda: model,
        stream_factory=lambda **kwargs: stream_calls.append(kwargs),
    )

    assert detector.wait_for_wake_word(stop_event) is None
    assert stream_calls == []


def test_wake_detector_validates_audio_contract():
    with pytest.raises(ValueError, match="16000"):
        WakeWordDetector(sample_rate=44100)

    with pytest.raises(ValueError, match="multiple of 1280"):
        WakeWordDetector(chunk_samples=1000)

    with pytest.raises(ValueError, match="threshold"):
        WakeWordDetector(threshold=1.1)

    with pytest.raises(ValueError, match="required_hits"):
        WakeWordDetector(required_hits=0)
