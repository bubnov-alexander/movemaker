from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Scene:
    id: int
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class WordTiming:
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: tuple[WordTiming, ...]


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    text: float
    motion: float
    audio: float
    duration: float
    total: float


@dataclass(frozen=True, slots=True)
class Candidate:
    id: int
    start: float
    end: float
    scene_ids: tuple[int, ...]
    text: str
    score: ScoreBreakdown | None = None
