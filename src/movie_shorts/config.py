from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from movie_shorts.errors import UserFacingError


@dataclass(frozen=True, slots=True)
class RunConfig:
    input_path: Path
    output_dir: Path
    count: int = 5
    min_duration: float = 20.0
    max_duration: float = 120.0
    language: str = "ru"
    device: Literal["auto", "cpu", "cuda"] = "auto"

    def __post_init__(self) -> None:
        if not 1 <= self.count <= 5:
            raise UserFacingError("Количество роликов должно быть от 1 до 5.")
        if self.min_duration <= 0 or self.max_duration <= 0:
            raise UserFacingError("Длительность ролика должна быть больше нуля.")
        if self.min_duration > self.max_duration:
            raise UserFacingError("Минимальная длительность не может быть больше максимальной.")

