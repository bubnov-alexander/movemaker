from pathlib import Path
from typing import Any

import ctranslate2

from movie_shorts.errors import UserFacingError
from movie_shorts.models import TranscriptSegment, WordTiming

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel: Any = None


def _compute_type(device: str, supported_cuda_types: set[str] | None = None) -> str:
    if device != "cuda":
        return "int8"

    supported_types = supported_cuda_types or ctranslate2.get_supported_compute_types("cuda")
    for compute_type in ("float16", "int8_float16", "int8_float32", "int8", "float32"):
        if compute_type in supported_types:
            return compute_type

    return "float32"


def _configure_onnx_logging() -> None:
    try:
        import onnxruntime
    except ImportError:
        return

    onnxruntime.set_default_logger_severity(3)


def transcribe(video_path: Path, language: str, device: str) -> list[TranscriptSegment]:
    if WhisperModel is None:
        raise UserFacingError("Не установлен faster-whisper. Установите зависимости проекта.")

    try:
        _configure_onnx_logging()
        model = WhisperModel(
            "small",
            device=device,
            compute_type=_compute_type(device),
        )
        detected_segments, _ = model.transcribe(
            str(video_path),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
        return [
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
                words=tuple(
                    WordTiming(start=float(word.start), end=float(word.end), text=word.word.strip())
                    for word in (segment.words or [])
                    if word.start is not None and word.end is not None and word.word.strip()
                ),
            )
            for segment in detected_segments
        ]
    except Exception as error:
        raise UserFacingError(
            "Не удалось распознать речь в видео. Подробности сохранены в logs/debug.log."
        ) from error
