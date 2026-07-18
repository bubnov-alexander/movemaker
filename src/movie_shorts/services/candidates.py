from collections.abc import Iterable

from movie_shorts.models import Candidate, Scene, TranscriptSegment, WordTiming


def words_for_interval(
    segments: Iterable[TranscriptSegment], start: float, end: float
) -> tuple[WordTiming, ...]:
    return tuple(
        word
        for segment in segments
        for word in segment.words
        if word.start < end and start < word.end
    )


def build_candidates(
    scenes: list[Scene],
    segments: list[TranscriptSegment],
    min_duration: float,
    max_duration: float,
) -> list[Candidate]:
    intervals: dict[tuple[float, float], tuple[Scene, ...]] = {}
    for start_index, first_scene in enumerate(scenes):
        window: list[Scene] = []
        for scene in scenes[start_index:]:
            if scene.end - first_scene.start > max_duration:
                break
            window.append(scene)
            duration = scene.end - first_scene.start
            if duration >= min_duration:
                intervals[(first_scene.start, scene.end)] = tuple(window)

    candidates: list[Candidate] = []
    for identifier, ((start, end), window) in enumerate(sorted(intervals.items()), start=1):
        words = words_for_interval(segments, start, end)
        text = " ".join(word.text for word in words)
        if not text:
            text = " ".join(segment.text for segment in segments if segment.start < end and start < segment.end)
        candidates.append(
            Candidate(
                id=identifier,
                start=start,
                end=end,
                scene_ids=tuple(scene.id for scene in window),
                text=text.strip(),
            )
        )
    return candidates
