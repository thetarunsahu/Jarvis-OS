from voice.stt_providers import FasterWhisperProvider


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeInfo:
    language = "hi"


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return [FakeSegment(" Chrome kholo ")], FakeInfo()


def test_faster_whisper_provider_loads_model_once_and_transcribes():
    created = []
    model = FakeModel()

    def factory(model_name, **kwargs):
        created.append((model_name, kwargs))
        return model

    stages = []
    provider = FasterWhisperProvider(
        model_name="small",
        device="cpu",
        compute_type="int8",
        model_factory=factory,
    )

    pcm = b"\x00\x00" * 160
    first = provider.transcribe_pcm(
        pcm,
        16000,
        stage_callback=stages.append,
    )
    second = provider.transcribe_pcm(pcm, 16000)

    assert first == "Chrome kholo"
    assert second == "Chrome kholo"
    assert provider.last_language == "hi"
    assert created == [
        (
            "small",
            {"device": "cpu", "compute_type": "int8"},
        )
    ]
    assert stages == ["loading_stt"]
    assert len(model.calls) == 2
    assert model.calls[0][1]["beam_size"] == 1
    assert model.calls[0][1]["vad_filter"] is True
