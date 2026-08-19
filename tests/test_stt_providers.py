from voice.stt_providers import FasterWhisperProvider


class FakeSegment:
    def __init__(
        self,
        text: str,
        *,
        avg_logprob: float = -0.2,
        no_speech_prob: float = 0.05,
    ) -> None:
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


class FakeInfo:
    def __init__(self, language="hi", language_probability=0.95) -> None:
        self.language = language
        self.language_probability = language_probability


class FakeModel:
    def __init__(self, segments=None, info=None) -> None:
        self.calls = []
        self.segments = segments or [FakeSegment(" Chrome kholo ")]
        self.info = info or FakeInfo()

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self.segments, self.info


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
    assert provider.last_language_probability == 0.95
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


def test_faster_whisper_rejects_unsupported_language():
    provider = FasterWhisperProvider(
        model_factory=lambda *args, **kwargs: FakeModel(
            info=FakeInfo(language="fr", language_probability=0.98)
        )
    )

    result = provider.transcribe_pcm(b"\x00\x00" * 160, 16000)

    assert result == ""
    assert provider.last_rejection == "unsupported_language:fr"


def test_faster_whisper_rejects_low_confidence_speech():
    provider = FasterWhisperProvider(
        model_factory=lambda *args, **kwargs: FakeModel(
            segments=[
                FakeSegment(
                    "random hallucination",
                    avg_logprob=-2.0,
                    no_speech_prob=0.90,
                )
            ]
        )
    )

    result = provider.transcribe_pcm(b"\x00\x00" * 160, 16000)

    assert result == ""
    assert provider.last_rejection == "low_speech_confidence"


def test_faster_whisper_rejects_low_language_confidence():
    provider = FasterWhisperProvider(
        model_factory=lambda *args, **kwargs: FakeModel(
            info=FakeInfo(language="en", language_probability=0.10)
        )
    )

    result = provider.transcribe_pcm(b"\x00\x00" * 160, 16000)

    assert result == ""
    assert provider.last_rejection == "low_language_confidence"
