import threading
import time

import numpy as np

from voice.audio_service import AudioFrame, AudioInputService
from voice.wake_word import WakeWordDetector


class FakeInputStream:
    def __init__(self, callback):
        self.callback = callback
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True

    def emit(self, samples, status=None):
        payload = np.asarray(samples, dtype=np.int16).tobytes()
        self.callback(payload, len(samples), None, status)


class FakeWakeModel:
    def __init__(self, scores):
        self.scores = iter(scores)
        self.reset_called = False

    def predict(self, frame):
        assert isinstance(frame, np.ndarray)
        assert frame.dtype == np.int16
        assert frame.size == 1280
        return next(self.scores)

    def reset(self):
        self.reset_called = True


class FakeAudioService:
    sample_rate = 16000

    def __init__(self, frames):
        self.frames = iter(frames)
        self.marked_sequence = None

    def latest_sequence(self):
        return 0

    def read_after(self, sequence, timeout=0.25):
        del sequence, timeout
        try:
            return next(self.frames)
        except StopIteration:
            return None

    def mark_wake_detected(self, sequence):
        self.marked_sequence = sequence


def pcm_frame(value=500, samples=320):
    return np.full(samples, value, dtype=np.int16)


def test_audio_service_keeps_one_stream_and_non_destructive_cursors():
    streams = []

    def factory(**kwargs):
        stream = FakeInputStream(kwargs["callback"])
        streams.append(stream)
        return stream

    service = AudioInputService(stream_factory=factory)
    cursor = service.latest_sequence()

    assert cursor == 0
    assert len(streams) == 1
    assert streams[0].started is True

    streams[0].emit(pcm_frame(600))
    first = service.read_after(0, timeout=0.01)
    same_for_second_reader = service.read_after(0, timeout=0.01)

    assert first is not None
    assert first.sequence == 1
    assert first.rms == 600
    assert same_for_second_reader == first
    assert len(streams) == 1

    service.stop()
    assert streams[0].stopped is True
    assert streams[0].closed is True


def test_audio_service_wake_marker_can_only_be_claimed_once():
    stream_holder = []

    def factory(**kwargs):
        stream = FakeInputStream(kwargs["callback"])
        stream_holder.append(stream)
        return stream

    service = AudioInputService(stream_factory=factory)
    service.latest_sequence()
    service.mark_wake_detected(42)

    assert service.claim_recent_wake(max_age=1.0) == 42
    assert service.claim_recent_wake(max_age=1.0) is None
    service.stop()


def test_wake_detector_consumes_shared_audio_without_opening_another_stream():
    frames = []
    captured_at = time.monotonic()
    for sequence in range(1, 13):
        samples = pcm_frame(700)
        frames.append(
            AudioFrame(
                sequence=sequence,
                pcm=samples.tobytes(),
                captured_at=captured_at + sequence * 0.02,
                rms=700,
            )
        )

    service = FakeAudioService(frames)
    model = FakeWakeModel(
        [
            {"hey_jarvis": 0.20},
            {"hey_jarvis": 0.82},
            {"hey_jarvis": 0.86},
        ]
    )
    detector = WakeWordDetector(
        threshold=0.70,
        required_hits=2,
        model_factory=lambda: model,
        audio_service=service,
    )

    result = detector.wait_for_wake_word(threading.Event())

    assert result is not None
    assert result.model_name == "hey_jarvis"
    assert result.score == 0.86
    assert service.marked_sequence == 12
    assert model.reset_called is True
