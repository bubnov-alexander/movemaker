from dataclasses import dataclass

from movie_shorts.config import RunConfig
from movie_shorts.models import Candidate, Scene
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
        score_candidates=lambda candidates, *args: candidates,
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
        score_candidates=lambda candidates, *args: candidates, select_candidates=lambda candidates, count: candidates,
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
        score_candidates=lambda items, *args: received.append(len(items)) or items,
        select_candidates=lambda items, count: items[:count], build_ass=lambda words, start: "",
        render_short=lambda *args: tmp_path / "short.mp4",
    )

    Pipeline(services).run(RunConfig(source, tmp_path / "output", analysis_limit=3))

    assert received == [3]
    assert (tmp_path / "output" / "prefiltered_candidates.json").exists()
