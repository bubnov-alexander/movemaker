from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from movie_shorts.config import BackgroundMusicConfig
from movie_shorts.models import Candidate


@dataclass(frozen=True, slots=True)
class MusicSelection:
    track: Literal["epic", "calm"]
    path: Path
    epic_score: float


def epic_score(candidate: Candidate) -> float:
    score = candidate.score
    if score is None:
        return 0.0

    return round(
        score.text * 0.35
        + score.motion * 0.30
        + score.audio * 0.20
        + score.total * 0.15,
        2,
    )


def select_background_music(candidate: Candidate, config: BackgroundMusicConfig) -> MusicSelection:
    score = epic_score(candidate)
    if score >= config.epic_threshold:
        return MusicSelection("epic", config.epic_path, score)

    return MusicSelection("calm", config.calm_path, score)
