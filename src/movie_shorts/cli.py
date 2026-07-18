from pathlib import Path
from typing import Annotated

import typer

from movie_shorts.config import RunConfig
from movie_shorts.errors import UserFacingError

app = typer.Typer(help="Локальное создание Shorts из видео.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Группа команд локального конвейера."""


@app.command(help="Создать Shorts из одного видеофайла.")
def create(
    input_path: Annotated[Path, typer.Argument(help="Путь к исходному видео.")],
    output_dir: Annotated[Path, typer.Option("--output", help="Папка для результата.")],
    count: Annotated[int, typer.Option(help="Количество роликов: от 1 до 5.")] = 5,
    min_duration: Annotated[float, typer.Option(help="Минимальная длительность в секундах.")] = 20.0,
    max_duration: Annotated[float, typer.Option(help="Максимальная длительность в секундах.")] = 120.0,
    language: Annotated[str, typer.Option(help="Язык распознавания речи.")] = "ru",
    device: Annotated[str, typer.Option(help="Устройство: auto, cpu или cuda.")] = "auto",
) -> None:
    """Проверить параметры и подготовить локальный запуск."""
    try:
        RunConfig(
            input_path=input_path,
            output_dir=output_dir,
            count=count,
            min_duration=min_duration,
            max_duration=max_duration,
            language=language,
            device=device,  # type: ignore[arg-type]
        )
    except UserFacingError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    typer.echo("Подготовка конвейера…")
