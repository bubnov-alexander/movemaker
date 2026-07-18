from pathlib import Path
from typing import Annotated

import typer

from movie_shorts.config import load_run_config
from movie_shorts.errors import UserFacingError
from movie_shorts.pipeline import Pipeline

app = typer.Typer(help="Локальное создание Shorts из видео.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Группа команд локального конвейера."""


@app.command(help="Создать Shorts из одного видеофайла.")
def create(
    input_path: Annotated[Path, typer.Argument(help="Путь к исходному видео.")],
    output_dir: Annotated[Path, typer.Option("--output", help="Папка для результата.")],
    count: Annotated[int | None, typer.Option(help="Количество роликов: от 1 до 5.")] = None,
    min_duration: Annotated[float | None, typer.Option(help="Минимальная длительность в секундах.")] = None,
    max_duration: Annotated[float | None, typer.Option(help="Максимальная длительность в секундах.")] = None,
    language: Annotated[str | None, typer.Option(help="Язык распознавания речи.")] = None,
    device: Annotated[str | None, typer.Option(help="Устройство: auto, cpu или cuda.")] = None,
    config_path: Annotated[Path | None, typer.Option("--config", help="Путь к YAML-конфигурации.")] = None,
) -> None:
    """Проверить параметры и подготовить локальный запуск."""
    try:
        config = load_run_config(
            input_path=input_path,
            output_dir=output_dir,
            config_path=config_path,
            count=count,
            min_duration=min_duration,
            max_duration=max_duration,
            language=language,
            device=device,
        )
    except UserFacingError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    report = Pipeline().run(config)
    for warning in report.warnings:
        typer.echo(warning)
    if not report.rendered_files:
        raise typer.Exit(code=1)
    typer.echo(f"Готово: создано роликов — {len(report.rendered_files)}.")
