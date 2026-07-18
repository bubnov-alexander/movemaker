import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from movie_shorts.models import Candidate, ScoreBreakdown

DEFAULT_KEYWORDS = {
    "убей": 20,
    "смерть": 20,
    "беги": 18,
    "помогите": 15,
    "монстр": 25,
    "кровь": 25,
    "пистолет": 18,
    "спасайся": 18,
}


def keyword_score(text: str, keywords: dict[str, int] = DEFAULT_KEYWORDS) -> float:
    return sum(keywords.get(word, 0) for word in re.findall(r"[^\W\d_]+", text.lower()))


def duration_score(duration: float) -> float:
    if 35 <= duration <= 75:
        return 100.0
    if 20 <= duration < 35:
        return (duration - 20) / 15 * 100
    if 75 < duration <= 120:
        return (120 - duration) / 45 * 100
    return 0.0


def prefilter_candidates(candidates: list[Candidate], limit: int) -> list[Candidate]:
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -(keyword_score(candidate.text) + duration_score(candidate.end - candidate.start)),
            candidate.start,
            candidate.id,
        ),
    )
    if len(ranked) <= limit:
        return ranked

    first_start = min(candidate.start for candidate in ranked)
    last_start = max(candidate.start for candidate in ranked)
    if first_start == last_start:
        return ranked[:limit]

    bucket_count = min(limit, len(ranked))
    bucket_width = (last_start - first_start) / bucket_count
    selected_by_bucket: dict[int, Candidate] = {}
    for candidate in ranked:
        bucket = min(int((candidate.start - first_start) / bucket_width), bucket_count - 1)
        center = first_start + (bucket + 0.5) * bucket_width
        current = selected_by_bucket.get(bucket)
        if current is None or _prefilter_key(candidate, center) < _prefilter_key(current, center):
            selected_by_bucket[bucket] = candidate

    selected = list(selected_by_bucket.values())
    selected_ids = {candidate.id for candidate in selected}
    for candidate in ranked:
        if len(selected) == limit:
            break
        if candidate.id not in selected_ids:
            selected.append(candidate)

    return sorted(selected, key=lambda candidate: (candidate.start, candidate.id))


def _prefilter_key(candidate: Candidate, bucket_center: float) -> tuple[float, float, float, int]:
    priority = keyword_score(candidate.text) + duration_score(candidate.end - candidate.start)
    return (-priority, abs(candidate.start - bucket_center), candidate.start, candidate.id)


def _motion_score(video_path: Path, candidate: Candidate) -> float:
    try:
        import cv2
    except ImportError:
        return 0.0

    capture = cv2.VideoCapture(str(video_path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
        if fps <= 0:
            return 0.0
        capture.set(cv2.CAP_PROP_POS_MSEC, candidate.start * 1000)
        frame_step = max(int(fps / 2), 1)
        previous = None
        differences: list[float] = []
        while capture.get(cv2.CAP_PROP_POS_MSEC) < candidate.end * 1000:
            ok, frame = capture.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                differences.append(float(cv2.absdiff(previous, gray).mean()))
            previous = gray
            for _ in range(frame_step - 1):
                if not capture.grab():
                    break
        return sum(differences) / len(differences) if differences else 0.0
    finally:
        capture.release()


def _audio_score(video_path: Path, candidate: Candidate) -> float:
    command = [
        "ffmpeg", "-v", "error", "-ss", str(candidate.start), "-t", str(candidate.end - candidate.start),
        "-i", str(video_path), "-af", "astats=metadata=1:reset=1", "-f", "null", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 0.0
    if result.returncode != 0:
        return 0.0
    values = [float(value) for value in re.findall(r"(?:Peak level dB|RMS level dB):\s*(-?\d+(?:\.\d+)?)", result.stderr)]
    return max(values, default=0.0)


def _normalize(values: list[float]) -> list[float]:
    if not values or max(values) == min(values):
        return [0.0] * len(values)
    lower, upper = min(values), max(values)
    return [(value - lower) / (upper - lower) * 100 for value in values]


def score_candidates(
    candidates: list[Candidate],
    video_path: Path,
    has_audio: bool,
    keywords: dict[str, int] = DEFAULT_KEYWORDS,
    progress: Callable[[int, int], None] | None = None,
) -> list[Candidate]:
    raw_text: list[float] = []
    raw_motion: list[float] = []
    raw_audio: list[float] = []
    total = len(candidates)
    for index, candidate in enumerate(candidates, start=1):
        raw_text.append(keyword_score(candidate.text, keywords))
        raw_motion.append(_motion_score(video_path, candidate))
        raw_audio.append(_audio_score(video_path, candidate) if has_audio else 0.0)
        if progress is not None:
            progress(index, total)
    text_scores, motion_scores, audio_scores = map(_normalize, (raw_text, raw_motion, raw_audio))

    return [
        Candidate(
            id=candidate.id,
            start=candidate.start,
            end=candidate.end,
            scene_ids=candidate.scene_ids,
            text=candidate.text,
            score=ScoreBreakdown(
                text=round(text_scores[index], 2),
                motion=round(motion_scores[index], 2),
                audio=round(audio_scores[index], 2),
                duration=round(duration_score(candidate.end - candidate.start), 2),
                total=round(
                    text_scores[index] * 0.30
                    + motion_scores[index] * 0.25
                    + audio_scores[index] * 0.20
                    + duration_score(candidate.end - candidate.start) * 0.25,
                    2,
                ),
            ),
        )
        for index, candidate in enumerate(candidates)
    ]
