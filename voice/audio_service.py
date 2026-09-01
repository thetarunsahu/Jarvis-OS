from __future__ import annotations

import atexit
import threading
import time
from array import array
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

import sounddevice as sd


StreamFactory = Callable[..., Any]


class AudioInputError(RuntimeError):
    """Raised when the shared microphone service cannot start or stream audio."""


@dataclass(frozen=True)
class AudioFrame:
    sequence: int
    pcm: bytes
    captured_at: float
    rms: int


class AudioInputService:
    """Own the microphone once and fan frames out to voice consumers.

    JARVIS used to let the wake-word detector and command recorder open their
    own microphone streams. That creates a hand-off gap after wake detection and
    can lose the beginning of a command. This service keeps one 16 kHz mono
    stream alive and exposes a small ring buffer plus cursor-based reads.
    """

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        frame_samples: int = 320,
        ring_seconds: float = 3.0,
        stream_factory: StreamFactory | None = None,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.frame_samples = int(frame_samples)
        self.ring_seconds = float(ring_seconds)
        self._stream_factory = stream_factory or sd.RawInputStream

        if self.sample_rate != 16000:
            raise ValueError("JARVIS shared audio service requires 16000 Hz")
        if self.frame_samples <= 0:
            raise ValueError("frame_samples must be positive")
        if self.ring_seconds <= 0:
            raise ValueError("ring_seconds must be positive")

        frames_per_second = self.sample_rate / self.frame_samples
        ring_size = max(8, int(frames_per_second * self.ring_seconds))

        self._condition = threading.Condition(threading.RLock())
        self._frames: deque[AudioFrame] = deque(maxlen=ring_size)
        self._sequence = 0
        self._stream: Any | None = None
        self._running = False
        self._starting = False
        self._last_status: str | None = None

        self._wake_sequence: int | None = None
        self._wake_marked_at: float | None = None
        self._wake_claimed = False

    @property
    def frame_duration(self) -> float:
        return self.frame_samples / self.sample_rate

    @property
    def running(self) -> bool:
        with self._condition:
            return self._running

    @property
    def last_status(self) -> str | None:
        with self._condition:
            return self._last_status

    def start(self) -> None:
        with self._condition:
            if self._running:
                return
            if self._starting:
                while self._starting and not self._running:
                    self._condition.wait(timeout=0.1)
                if self._running:
                    return
            self._starting = True

        stream = None
        try:
            stream = self._stream_factory(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.frame_samples,
                callback=self._on_audio,
            )
            start = getattr(stream, "start", None)
            if not callable(start):
                raise AudioInputError("microphone stream does not support start()")
            start()
        except Exception as error:
            if stream is not None:
                try:
                    close = getattr(stream, "close", None)
                    if callable(close):
                        close()
                except Exception:
                    pass
            with self._condition:
                self._starting = False
                self._condition.notify_all()
            if isinstance(error, AudioInputError):
                raise
            raise AudioInputError(f"Shared microphone could not start: {error}") from error

        with self._condition:
            self._stream = stream
            self._running = True
            self._starting = False
            self._condition.notify_all()

    def stop(self) -> None:
        with self._condition:
            stream = self._stream
            self._stream = None
            self._running = False
            self._starting = False
            self._condition.notify_all()

        if stream is not None:
            for method_name in ("stop", "close"):
                try:
                    method = getattr(stream, method_name, None)
                    if callable(method):
                        method()
                except Exception:
                    pass

    def latest_sequence(self) -> int:
        self.start()
        with self._condition:
            return self._sequence

    def read_after(self, sequence: int, *, timeout: float = 0.25) -> AudioFrame | None:
        """Return the first buffered frame newer than ``sequence``.

        Multiple independent readers can keep their own cursor. Reading does not
        remove frames, which is what lets wake detection and command capture use
        the same physical microphone without racing over a queue.
        """
        self.start()
        deadline = time.monotonic() + max(0.0, float(timeout))

        with self._condition:
            while True:
                for frame in self._frames:
                    if frame.sequence > sequence:
                        return frame

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(timeout=remaining)

    def recent_frames(
        self,
        *,
        seconds: float = 0.5,
        before_sequence: int | None = None,
    ) -> tuple[AudioFrame, ...]:
        self.start()
        max_frames = max(1, int(float(seconds) / self.frame_duration))
        with self._condition:
            items = [
                frame
                for frame in self._frames
                if before_sequence is None or frame.sequence <= before_sequence
            ]
        return tuple(items[-max_frames:])

    def mark_wake_detected(self, sequence: int) -> None:
        with self._condition:
            self._wake_sequence = int(sequence)
            self._wake_marked_at = time.monotonic()
            self._wake_claimed = False

    def claim_recent_wake(self, *, max_age: float = 2.0) -> int | None:
        """Claim the latest wake hand-off once for command capture."""
        with self._condition:
            if (
                self._wake_sequence is None
                or self._wake_marked_at is None
                or self._wake_claimed
                or time.monotonic() - self._wake_marked_at > float(max_age)
            ):
                return None
            self._wake_claimed = True
            return self._wake_sequence

    def _on_audio(self, indata, frames, time_info, status) -> None:
        del frames, time_info
        payload = bytes(indata)
        if not payload:
            return

        status_text = str(status).strip() if status else None
        bytes_per_frame = self.frame_samples * 2

        for offset in range(0, len(payload), bytes_per_frame):
            chunk = payload[offset : offset + bytes_per_frame]
            if len(chunk) != bytes_per_frame:
                continue

            with self._condition:
                self._sequence += 1
                frame = AudioFrame(
                    sequence=self._sequence,
                    pcm=chunk,
                    captured_at=time.monotonic(),
                    rms=self._pcm_rms(chunk),
                )
                self._frames.append(frame)
                if status_text:
                    self._last_status = status_text
                self._condition.notify_all()

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


_default_service: AudioInputService | None = None
_default_service_lock = threading.Lock()


def get_audio_input_service() -> AudioInputService:
    global _default_service
    with _default_service_lock:
        if _default_service is None:
            _default_service = AudioInputService()
            atexit.register(_default_service.stop)
        return _default_service
