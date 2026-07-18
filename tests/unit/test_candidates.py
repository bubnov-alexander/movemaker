from movie_shorts.models import Scene
from movie_shorts.services.candidates import build_candidates


def test_builder_merges_adjacent_scenes_until_minimum_duration() -> None:
    scenes = [Scene(1, 0, 8), Scene(2, 8, 17), Scene(3, 17, 28)]

    candidates = build_candidates(scenes, [], min_duration=20, max_duration=120)

    assert candidates[0].start == 0
    assert candidates[0].end == 28
    assert candidates[0].scene_ids == (1, 2, 3)


def test_builder_never_returns_interval_longer_than_maximum() -> None:
    scenes = [Scene(1, 0, 70), Scene(2, 70, 140)]

    candidates = build_candidates(scenes, [], min_duration=20, max_duration=120)

    assert all(candidate.end - candidate.start <= 120 for candidate in candidates)
