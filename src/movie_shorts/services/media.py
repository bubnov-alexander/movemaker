import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from movie_shorts.errors import UserFacingError


@dataclass(frozen=True, slots=True)
class MediaInfo:
    duration: float
    has_video: bool
    has_audio: bool


def probe_media(video_path: Path) -> MediaInfo:
    if not video_path.is_file():
        raise UserFacingError("Не удалось открыть видео: проверьте путь и формат файла.")

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise UserFacingError("Не найден ffprobe. Установите FFmpeg и повторите запуск.") from error

    if result.returncode != 0:
        raise UserFacingError("Не удалось прочитать параметры видео. Проверьте формат файла.")

    try:
        payload = json.loads(result.stdout)
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise UserFacingError("В видео не удалось определить длительность.") from error

    stream_types = {stream.get("codec_type") for stream in payload.get("streams", [])}
    if "video" not in stream_types:
        raise UserFacingError("В файле не найден видеопоток.")
    if duration <= 0:
        raise UserFacingError("Длительность видео должна быть больше нуля.")

    return MediaInfo(duration=duration, has_video=True, has_audio="audio" in stream_types)


def cuda_available() -> bool:
    try:
        import ctranslate2

        return bool(ctranslate2.get_supported_compute_types("cuda"))
    except (ImportError, RuntimeError, ValueError):
        return False


def resolve_device(requested: str) -> str:
    if requested == "auto":
        return "cuda" if cuda_available() else "cpu"
    if requested in {"cpu", "cuda"}:
        if requested == "cuda" and not cuda_available():
            raise UserFacingError("CUDA недоступна. Выберите --device cpu или --device auto.")
        return requested
    raise UserFacingError("Устройство должно быть одним из значений: auto, cpu, cuda.")
