import sys

from movie_shorts.models import WordTiming
from movie_shorts.services.transcript import _compute_type, _configure_onnx_logging, transcribe


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


def test_compute_type_uses_int8_float32_when_float16_is_unavailable() -> None:
    supported_types = {"int8", "float32", "int8_float32"}

    compute_type = _compute_type("cuda", supported_types)

    assert compute_type == "int8_float32"


def test_configure_onnx_logging_hides_warnings(monkeypatch) -> None:
    class FakeOnnxRuntime:
        severity: int | None = None

        @classmethod
        def set_default_logger_severity(cls, severity: int) -> None:
            cls.severity = severity

    monkeypatch.setitem(sys.modules, "onnxruntime", FakeOnnxRuntime)

    _configure_onnx_logging()

    assert FakeOnnxRuntime.severity == 3
