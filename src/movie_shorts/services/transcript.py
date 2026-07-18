from pathlib import Path
from typing import Any

from movie_shorts.errors import UserFacingError
from movie_shorts.models import TranscriptSegment, WordTiming

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel: Any = None


def transcribe(video_path: Path, language: str, device: str) -> list[TranscriptSegment]:
    if WhisperModel is None:
        raise UserFacingError("Не установлен faster-whisper. Установите зависимости проекта.")

    try:
        model = WhisperModel(
            "small",
            device=device,
            compute_type="float16" if device == "cuda" else "int8",
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
