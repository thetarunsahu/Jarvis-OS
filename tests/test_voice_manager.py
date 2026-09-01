import speech_recognition as sr

from voice.voice_manager import VoiceManager


class FakeRecording:
    def __init__(self, frames: int) -> None:
        self.frames = frames

    def tobytes(self) -> bytes:
        return b"\x00\x00" * self.frames


class FakeRecognizer:
    def record(self, source):
        return "audio"

    def recognize_google(self, audio):
        assert audio == "audio"
        return "open notepad"


class FakeEngine:
    def __init__(self) -> None:
        self.properties = {}
        self.spoken = []
        self.ran = False
        self.stopped = False

    def setProperty(self, name, value):
        self.properties[name] = value

    def say(self, text):
        self.spoken.append(text)

    def runAndWait(self):
        self.ran = True

    def stop(self):
        self.stopped = True


def test_listen_returns_recognized_text():
    captured = {}

    def recorder(frames, **kwargs):
        captured["frames"] = frames
        captured.update(kwargs)
        return FakeRecording(frames)

    waited = []
    manager = VoiceManager(
        recognizer=FakeRecognizer(),
        recorder=recorder,
        wait_for_recording=lambda: waited.append(True),
    )

    result = manager.listen(duration=0.1, sample_rate=16000)

    assert result == "open notepad"
    assert captured["frames"] == 1600
    assert captured["samplerate"] == 16000
    assert captured["channels"] == 1
    assert captured["dtype"] == "int16"
    assert waited == [True]


def test_listen_returns_empty_string_for_unrecognized_audio():
    class UnknownRecognizer(FakeRecognizer):
        def recognize_google(self, audio):
            raise sr.UnknownValueError()

    manager = VoiceManager(
        recognizer=UnknownRecognizer(),
        recorder=lambda frames, **kwargs: FakeRecording(frames),
        wait_for_recording=lambda: None,
    )

    assert manager.listen(duration=0.05) == ""


def test_speak_uses_lazy_engine_factory():
    engine = FakeEngine()
    factory_calls = []

    def engine_factory():
        factory_calls.append(True)
        return engine

    manager = VoiceManager(engine_factory=engine_factory, rate=180, volume=0.8)

    assert factory_calls == []

    manager.speak("Systems online")

    assert factory_calls == [True]
    assert engine.properties == {"rate": 180, "volume": 0.8}
    assert engine.spoken == ["Systems online"]
    assert engine.ran is True
    assert engine.stopped is True
