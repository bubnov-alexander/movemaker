import subprocess
from pathlib import Path

from movie_shorts.errors import UserFacingError
from movie_shorts.models import Candidate
from movie_shorts.config import BackgroundMusicConfig
from movie_shorts.services.music import MusicSelection


def render_command(
    source_path: Path,
    candidate: Candidate,
    subtitle_path: Path | None,
    target_path: Path,
    music: MusicSelection | None = None,
    music_config: BackgroundMusicConfig | None = None,
    has_source_audio: bool = True,
    layout_background_path: Path | None = None,
) -> list[str]:
    foreground = "scale=1080:1920:force_original_aspect_ratio=decrease"
    background = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10"
    filter_parts = [f"[0:v]{background}[base]"]
    if layout_background_path is None:
        filter_parts.extend([f"[0:v]{foreground}[fg]", "[base][fg]overlay=(W-w)/2:(H-h)/2[video]"])
    else:
        filter_parts.extend([
            "[1:v]scale=1080:480:force_original_aspect_ratio=increase,crop=1080:480[top]",
            "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[middle]",
            "[base][top]overlay=0:0[with_top]",
            "[with_top][middle]overlay=0:480[video]",
        ])
    if subtitle_path is not None:
        escaped_subtitle = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")
        filter_parts.append(f"[video]ass={escaped_subtitle}[out]")
    else:
        filter_parts.append("[video]null[out]")

    command = [
        "ffmpeg", "-y", "-ss", str(candidate.start), "-i", str(source_path),
    ]
    music_input_index = 1
    if layout_background_path is not None:
        command.extend(["-stream_loop", "-1", "-i", str(layout_background_path)])
        music_input_index = 2
    audio_map = "0:a?"
    if music is not None:
        if music_config is None:
            raise ValueError("Для фоновой музыки требуется конфигурация.")
        duration = candidate.end - candidate.start
        command.extend(["-stream_loop", "-1", "-i", str(music.path)])
        filter_parts.append(
            f"[{music_input_index}:a]volume={music_config.quiet_volume},atrim=duration={duration},asetpts=N/SR/TB[music]"
        )
        if has_source_audio:
            filter_parts.extend([
                "[0:a]asplit=2[original][sidechain]",
                "[music][sidechain]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=300[ducked]",
                f"[ducked]volume={music_config.max_volume / music_config.quiet_volume}[music_limited]",
                "[original][music_limited]amix=inputs=2:duration=first:normalize=0[mixed]",
            ])
            audio_map = "[mixed]"
        else:
            filter_parts.append(f"[music]volume={music_config.max_volume / music_config.quiet_volume}[music_limited]")
            audio_map = "[music_limited]"

    command.extend([
        "-t", str(candidate.end - candidate.start), "-filter_complex", ";".join(filter_parts),
        "-map", "[out]", "-map", audio_map, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart", str(target_path),
    ])
    return command


def render_short(
    source_path: Path,
    candidate: Candidate,
    subtitle_path: Path | None,
    target_path: Path,
    debug_log: Path | None = None,
    music: MusicSelection | None = None,
    music_config: BackgroundMusicConfig | None = None,
    has_source_audio: bool = True,
    layout_background_path: Path | None = None,
) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(f"{target_path.stem}.tmp{target_path.suffix}")
    if music is not None and not music.path.is_file():
        raise UserFacingError(f"Не найден фоновый трек: {music.path}")
    if layout_background_path is not None and not layout_background_path.is_file():
        raise UserFacingError(f"Не найден видеофон для верхней части: {layout_background_path}")
    command = render_command(
        source_path,
        candidate,
        subtitle_path,
        temporary_path,
        music,
        music_config,
        has_source_audio,
        layout_background_path,
    )
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
