import subprocess
from pathlib import Path

from movie_shorts.errors import UserFacingError
from movie_shorts.models import Candidate


def render_command(
    source_path: Path,
    candidate: Candidate,
    subtitle_path: Path | None,
    target_path: Path,
) -> list[str]:
    foreground = "scale=1080:1920:force_original_aspect_ratio=decrease"
    background = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10"
    filter_parts = [f"[0:v]{background}[bg]", f"[0:v]{foreground}[fg]", "[bg][fg]overlay=(W-w)/2:(H-h)/2"]
    if subtitle_path is not None:
        escaped_subtitle = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")
        filter_parts[-1] += f",ass={escaped_subtitle}"
    filter_parts[-1] += "[out]"

    return [
        "ffmpeg", "-y", "-ss", str(candidate.start), "-i", str(source_path),
        "-t", str(candidate.end - candidate.start), "-filter_complex", ";".join(filter_parts),
        "-map", "[out]", "-map", "0:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart", str(target_path),
    ]


def render_short(
    source_path: Path,
    candidate: Candidate,
    subtitle_path: Path | None,
    target_path: Path,
    debug_log: Path | None = None,
) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(f"{target_path.stem}.tmp{target_path.suffix}")
    command = render_command(source_path, candidate, subtitle_path, temporary_path)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise UserFacingError("Не найден FFmpeg. Установите FFmpeg и повторите запуск.") from error

    if result.returncode != 0 or not temporary_path.exists() or temporary_path.stat().st_size == 0:
        if temporary_path.exists():
            temporary_path.unlink()
        if debug_log is not None:
            debug_log.parent.mkdir(parents=True, exist_ok=True)
            debug_log.write_text(result.stderr, encoding="utf-8")
        raise UserFacingError("Не удалось создать итоговый ролик. Подробности сохранены в logs/debug.log.")

    temporary_path.replace(target_path)
    return target_path
