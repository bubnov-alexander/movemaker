import re
import subprocess
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
    return sorted(
        candidates,
        key=lambda candidate: (
            -(keyword_score(candidate.text) + duration_score(candidate.end - candidate.start)),
            candidate.start,
            candidate.id,
        ),
    )[:limit]


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
    candidates: list[Candidate], video_path: Path, has_audio: bool, keywords: dict[str, int] = DEFAULT_KEYWORDS
) -> list[Candidate]:
    raw_text = [keyword_score(candidate.text, keywords) for candidate in candidates]
    raw_motion = [_motion_score(video_path, candidate) for candidate in candidates]
    raw_audio = [_audio_score(video_path, candidate) if has_audio else 0.0 for candidate in candidates]
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
