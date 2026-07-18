from movie_shorts.models import Scene
from movie_shorts.services.scenes import detect_scenes


class Timecode:
    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def get_seconds(self) -> float:
        return self.seconds


def test_detector_converts_timecodes_to_ordered_scenes(monkeypatch, tmp_path) -> None:
    def fake_detect(*args, **kwargs):
        return [(Timecode(4.2), Timecode(9.0)), (Timecode(0.0), Timecode(4.2))]

    monkeypatch.setattr("movie_shorts.services.scenes.detect", fake_detect)

    scenes = detect_scenes(tmp_path / "film.mp4", duration=9.0)

    assert scenes == [Scene(id=1, start=0.0, end=4.2), Scene(id=2, start=4.2, end=9.0)]
