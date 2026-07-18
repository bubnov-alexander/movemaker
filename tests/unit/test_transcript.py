from movie_shorts.models import WordTiming
from movie_shorts.services.transcript import transcribe


class FakeWord:
    start = 0.1
    end = 0.4
    word = " Привет"


class FakeSegment:
    start = 0.0
    end = 0.5
    text = " Привет"
    words = [FakeWord()]


class FakeModel:
    def transcribe(self, *args, **kwargs):
        return [FakeSegment()], {"language": "ru"}


class FakeModelFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, *args, **kwargs):
        self.calls.append(kwargs)
        return FakeModel()


def test_transcriber_preserves_words_and_language(monkeypatch, tmp_path) -> None:
    factory = FakeModelFactory()
    monkeypatch.setattr("movie_shorts.services.transcript.WhisperModel", factory)

    segments = transcribe(tmp_path / "film.mp4", language="ru", device="cpu")

    assert factory.calls[0]["device"] == "cpu"
    assert segments[0].words[0] == WordTiming(start=0.1, end=0.4, text="Привет")
