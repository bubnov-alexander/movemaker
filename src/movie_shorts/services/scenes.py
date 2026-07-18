from pathlib import Path
from typing import Any, Callable

from movie_shorts.errors import UserFacingError
from movie_shorts.models import Scene

try:
    from scenedetect import ContentDetector, detect
except ImportError:
    ContentDetector = None  # type: ignore[assignment]
    detect: Callable[..., list[tuple[Any, Any]]] | None = None


def detect_scenes(video_path: Path, duration: float) -> list[Scene]:
    if detect is None:
        raise UserFacingError("Не установлен PySceneDetect. Установите зависимости проекта.")

    detector = ContentDetector() if ContentDetector is not None else None
    detected_scenes = detect(str(video_path), detector=detector) if detector is not None else detect(str(video_path))
    intervals = sorted(
        (
            (start.get_seconds(), end.get_seconds())
            for start, end in detected_scenes
            if end.get_seconds() > start.get_seconds()
        ),
        key=lambda interval: interval[0],
    )
    if not intervals:
        intervals = [(0.0, duration)]

    return [Scene(id=index, start=start, end=end) for index, (start, end) in enumerate(intervals, start=1)]
