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


def test_builder_skips_candidates_from_intro() -> None:
    scenes = [Scene(1, 0, 20), Scene(2, 20, 40), Scene(3, 40, 65), Scene(4, 65, 90)]

    candidates = build_candidates(scenes, [], min_duration=20, max_duration=120, skip_intro=40)

    assert candidates
    assert all(candidate.start >= 40 for candidate in candidates)


def test_builder_excludes_intervals_that_reach_outro() -> None:
    scenes = [Scene(1, 0, 30), Scene(2, 30, 60), Scene(3, 60, 90)]

    candidates = build_candidates(scenes, [], 20, 60, video_duration=90, skip_outro=45)

    assert candidates
    assert all(candidate.end <= 45 for candidate in candidates)
