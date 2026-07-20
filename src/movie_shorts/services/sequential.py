from movie_shorts.models import Candidate, Scene, TranscriptSegment
from movie_shorts.services.candidates import words_for_interval


def build_sequential_candidates(
    scenes: list[Scene],
    segments: list[TranscriptSegment],
    start: float,
    end: float,
    target_duration: float = 60.0,
    min_duration: float = 45.0,
    max_duration: float = 75.0,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    current_start = start
    identifier = 1
    while current_start < end:
        remaining = end - current_start
        if remaining <= max_duration:
            current_end = end
        else:
            boundaries = [scene.end for scene in scenes if current_start + min_duration <= scene.end <= current_start + max_duration]
            if boundaries:
                current_end = min(boundaries, key=lambda boundary: abs(boundary - (current_start + target_duration)))
            else:
                current_end = current_start + target_duration
        words = words_for_interval(segments, current_start, current_end)
        text = " ".join(word.text for word in words)
        if not text:
            text = " ".join(segment.text for segment in segments if segment.start < current_end and current_start < segment.end)
        scene_ids = tuple(scene.id for scene in scenes if scene.start < current_end and current_start < scene.end)
        candidates.append(Candidate(identifier, current_start, current_end, scene_ids, text.strip()))
        identifier += 1
        current_start = current_end
    return candidates
