from movie_shorts.models import Scene, TranscriptSegment
from movie_shorts.services.sequential import build_sequential_candidates


def test_builds_contiguous_parts_near_sixty_seconds() -> None:
    scenes = [Scene(1, 0, 30), Scene(2, 30, 60), Scene(3, 60, 90), Scene(4, 90, 120)]

    candidates = build_sequential_candidates(scenes, [], 0, 120)

    assert [(item.start, item.end) for item in candidates] == [(0, 60), (60, 120)]
