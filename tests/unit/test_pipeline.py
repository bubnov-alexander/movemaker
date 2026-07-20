from dataclasses import dataclass
from pathlib import Path

import pytest

from movie_shorts.config import BackgroundMusicConfig, RunConfig
from movie_shorts.errors import UserFacingError
from movie_shorts.models import Candidate, Scene, ScoreBreakdown
from movie_shorts.pipeline import Pipeline, Services
from movie_shorts.services.media import MediaInfo
from movie_shorts.storage import RunStorage


@dataclass
class FakeSceneDetector:
    calls: int = 0

    def __call__(self, *args):
        self.calls += 1
        return [Scene(1, 0, 25)]


def test_pipeline_reuses_completed_scenes_stage(tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    storage = RunStorage.create(tmp_path / "output", {})
    storage.save_stage("scenes", [{"id": 1, "start": 0, "end": 25}])
    detector = FakeSceneDetector()
    services = Services(
        probe_media=lambda path: MediaInfo(25, True, False),
        resolve_device=lambda device: "cpu",
        detect_scenes=detector,
        transcribe=lambda *args: [],
        build_candidates=lambda *args: [Candidate(1, 0, 25, (1,), "")],
        score_candidates=lambda candidates, *args, **kwargs: candidates,
        select_candidates=lambda candidates, count: candidates,
        build_ass=lambda words, start: "",
        render_short=lambda *args: tmp_path / "output" / "shorts" / "short-01.mp4",
    )

    report = Pipeline(services).run(RunConfig(source, tmp_path / "output", min_duration=20, max_duration=120))

    assert detector.calls == 0
    assert report.rendered_files


def test_pipeline_serializes_path_parameters_for_a_new_run(tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    services = Services(
        probe_media=lambda path: MediaInfo(25, True, False), resolve_device=lambda device: "cpu",
        detect_scenes=lambda *args: [Scene(1, 0, 25)], transcribe=lambda *args: [],
        build_candidates=lambda *args: [Candidate(1, 0, 25, (1,), "")],
        score_candidates=lambda candidates, *args, **kwargs: candidates, select_candidates=lambda candidates, count: candidates,
        build_ass=lambda words, start: "", render_short=lambda *args: tmp_path / "short.mp4",
    )

    Pipeline(services).run(RunConfig(source, tmp_path / "fresh-output", min_duration=20, max_duration=120))

    assert (tmp_path / "fresh-output" / "manifest.json").exists()


def test_pipeline_passes_only_analysis_limit_to_precise_scorer(tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    received: list[int] = []
    candidates = [Candidate(index, index * 30, index * 30 + 25, (index,), "беги" if index == 1 else "") for index in range(1, 41)]
    services = Services(
        probe_media=lambda path: MediaInfo(1_300, True, False), resolve_device=lambda device: "cpu",
        detect_scenes=lambda *args: [], transcribe=lambda *args: [], build_candidates=lambda *args: candidates,
        score_candidates=lambda items, *args, **kwargs: received.append(len(items)) or items,
        select_candidates=lambda items, count: items[:count], build_ass=lambda words, start: "",
        render_short=lambda *args: tmp_path / "short.mp4",
    )

    Pipeline(services).run(RunConfig(source, tmp_path / "output", analysis_limit=3))

    assert received == [3]
    assert (tmp_path / "output" / "prefiltered_candidates.json").exists()


def test_pipeline_logs_original_transcription_error(tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()

    def fail_transcription(*args):
        try:
            raise RuntimeError("CUDA model загрузить не удалось")
        except RuntimeError as error:
            raise UserFacingError("Не удалось распознать речь в видео.") from error

    services = Services(
        probe_media=lambda path: MediaInfo(25, True, False), resolve_device=lambda device: "cpu",
        detect_scenes=lambda *args: [Scene(1, 0, 25)], transcribe=fail_transcription,
        build_candidates=lambda *args: [], score_candidates=lambda *args, **kwargs: [],
        select_candidates=lambda *args: [], build_ass=lambda *args: "", render_short=lambda *args: tmp_path / "short.mp4",
    )

    with pytest.raises(UserFacingError, match="Не удалось распознать речь"):
        Pipeline(services).run(RunConfig(source, tmp_path / "output"))

    debug_log = (tmp_path / "output" / "logs" / "debug.log").read_text(encoding="utf-8")
    assert "CUDA model загрузить не удалось" in debug_log


def test_pipeline_records_and_passes_selected_music(tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    received = []
    candidate = Candidate(1, 0, 25, (1,), "беги монстр", ScoreBreakdown(90, 80, 70, 100, 85))
    services = Services(
        probe_media=lambda path: MediaInfo(25, True, False), resolve_device=lambda device: "cpu",
        detect_scenes=lambda *args: [Scene(1, 0, 25)], transcribe=lambda *args: [],
        build_candidates=lambda *args: [candidate], score_candidates=lambda items, *args, **kwargs: items,
        select_candidates=lambda items, count: items, build_ass=lambda words, start: "",
        render_short=lambda *args, **kwargs: received.append(kwargs["music"]) or tmp_path / "short.mp4",
    )
    music_config = BackgroundMusicConfig(Path("music/yaya.mp3"), Path("music/altyn.mp3"))

    Pipeline(services).run(RunConfig(source, tmp_path / "out", background_music=music_config))

    assert received[0].track == "epic"
    metadata = RunStorage(tmp_path / "out").manifest()["shorts"]["short-01"]["music"]
    assert metadata["track"] == "epic"


def test_pipeline_passes_layout_background_path_to_renderer(tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    received: dict[str, Path] = {}
    services = Services(
        probe_media=lambda path: MediaInfo(25, True, False), resolve_device=lambda device: "cpu",
        detect_scenes=lambda *args: [Scene(1, 0, 25)], transcribe=lambda *args: [],
        build_candidates=lambda *args: [Candidate(1, 0, 25, (1,), "")],
        score_candidates=lambda items, *args, **kwargs: items, select_candidates=lambda items, count: items,
        build_ass=lambda words, start: "",
        render_short=lambda *args, **kwargs: received.update(kwargs) or tmp_path / "short.mp4",
    )
    layout_background = Path("backgrounds/background.mp4")

    Pipeline(services).run(RunConfig(source, tmp_path / "out", layout_background_path=layout_background))

    assert received["layout_background_path"] == layout_background
