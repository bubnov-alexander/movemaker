from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from movie_shorts.errors import UserFacingError


@dataclass(frozen=True, slots=True)
class BackgroundMusicConfig:
    epic_path: Path
    calm_path: Path
    max_volume: float = 0.12
    quiet_volume: float = 0.18
    epic_threshold: float = 60.0

    def __post_init__(self) -> None:
        if not 0 < self.max_volume <= self.quiet_volume <= 1:
            raise UserFacingError("Громкость фоновой музыки должна быть в диапазоне от 0 до 1.")
        if not 0 <= self.epic_threshold <= 100:
            raise UserFacingError("Порог эпичности должен быть от 0 до 100.")


@dataclass(frozen=True, slots=True)
class RunConfig:
    input_path: Path
    output_dir: Path
    count: int = 5
    min_duration: float = 20.0
    max_duration: float = 120.0
    skip_intro: float = 0.0
    skip_outro: float = 60.0
    analysis_limit: int = 30
    language: str = "ru"
    device: Literal["auto", "cpu", "cuda"] = "auto"
    background_music: BackgroundMusicConfig | None = None
    layout_background_path: Path | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.count <= 5:
            raise UserFacingError("Количество роликов должно быть от 1 до 5.")
        if self.min_duration <= 0 or self.max_duration <= 0:
            raise UserFacingError("Длительность ролика должна быть больше нуля.")
        if self.min_duration > self.max_duration:
            raise UserFacingError("Минимальная длительность не может быть больше максимальной.")
        if self.skip_intro < 0:
            raise UserFacingError("Длительность пропуска начала не может быть отрицательной.")
        if self.skip_outro < 0:
            raise UserFacingError("Длительность пропуска конца не может быть отрицательной.")
        if self.analysis_limit < 1:
            raise UserFacingError("Лимит анализа должен быть больше нуля.")


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
        allowed = {"count", "min_duration", "max_duration", "skip_intro", "skip_outro", "analysis_limit", "language", "device", "keywords", "weights", "background_music", "layout_background_path"}
        unknown = set(loaded) - allowed
        if unknown:
            raise UserFacingError(f"Неизвестные параметры конфигурации: {', '.join(sorted(unknown))}.")
        values.update(loaded)

    values.update({key: value for key, value in overrides.items() if value is not None})
    background_music = values.get("background_music")
    if background_music is not None and not isinstance(background_music, dict):
        raise UserFacingError("Параметр background_music должен быть объектом.")

    music_config = None
    if isinstance(background_music, dict):
        epic_path = background_music.get("epic_path")
        calm_path = background_music.get("calm_path")
        if epic_path is None and calm_path is None:
            raise UserFacingError("Для фоновой музыки укажите epic_path или calm_path.")
        if epic_path is None:
            epic_path = calm_path
        if calm_path is None:
            calm_path = epic_path
        music_config = BackgroundMusicConfig(
            epic_path=Path(str(epic_path)),
            calm_path=Path(str(calm_path)),
            max_volume=float(background_music.get("max_volume", 0.12)),
            quiet_volume=float(background_music.get("quiet_volume", 0.18)),
            epic_threshold=float(background_music.get("epic_threshold", 60.0)),
        )

    return RunConfig(
        input_path=Path(input_path),
        output_dir=output_dir,
        count=int(values.get("count", 5)),
        min_duration=float(values.get("min_duration", 20.0)),
        max_duration=float(values.get("max_duration", 120.0)),
        skip_intro=float(values.get("skip_intro", 0.0)),
        skip_outro=float(values.get("skip_outro", 60.0)),
        analysis_limit=int(values.get("analysis_limit", 30)),
        language=str(values.get("language", "ru")),
        device=str(values.get("device", "auto")),  # type: ignore[arg-type]
        background_music=music_config,
        layout_background_path=Path(str(values["layout_background_path"])) if values.get("layout_background_path") is not None else None,
    )
