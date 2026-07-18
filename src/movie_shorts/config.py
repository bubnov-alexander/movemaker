from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

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


def load_run_config(
    input_path: str | Path,
    output_dir: Path,
    config_path: Path | None = None,
    **overrides: object,
) -> RunConfig:
    values: dict[str, object] = {}
    if config_path is not None:
        try:
            with config_path.open(encoding="utf-8") as file:
                loaded = yaml.safe_load(file) or {}
        except FileNotFoundError as error:
            raise UserFacingError("Файл конфигурации не найден.") from error
        except yaml.YAMLError as error:
            raise UserFacingError("Не удалось прочитать YAML-конфигурацию.") from error
        if not isinstance(loaded, dict):
            raise UserFacingError("Конфигурация должна быть YAML-объектом с параметрами.")
        allowed = {"count", "min_duration", "max_duration", "language", "device", "keywords", "weights"}
        unknown = set(loaded) - allowed
        if unknown:
            raise UserFacingError(f"Неизвестные параметры конфигурации: {', '.join(sorted(unknown))}.")
        values.update(loaded)

    values.update({key: value for key, value in overrides.items() if value is not None})
    return RunConfig(
        input_path=Path(input_path),
        output_dir=output_dir,
        count=int(values.get("count", 5)),
        min_duration=float(values.get("min_duration", 20.0)),
        max_duration=float(values.get("max_duration", 120.0)),
        language=str(values.get("language", "ru")),
        device=str(values.get("device", "auto")),  # type: ignore[arg-type]
    )
