from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
import traceback
from typing import Any

from movie_shorts.config import RunConfig
from movie_shorts.errors import UserFacingError
from movie_shorts.models import Candidate, Scene, ScoreBreakdown, TranscriptSegment, WordTiming
from movie_shorts.services.candidates import build_candidates, select_candidates, words_for_interval
from movie_shorts.services.media import probe_media, resolve_device
from movie_shorts.services.renderer import render_short
from movie_shorts.services.scenes import detect_scenes
from movie_shorts.services.scoring import prefilter_candidates, score_candidates
from movie_shorts.services.subtitles import build_ass
from movie_shorts.services.transcript import transcribe
from movie_shorts.storage import RunStorage


@dataclass(frozen=True, slots=True)
class RunReport:
    rendered_files: tuple[Path, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Services:
    probe_media: Callable[..., Any]
    resolve_device: Callable[..., str]
    detect_scenes: Callable[..., list[Scene]]
    transcribe: Callable[..., list[TranscriptSegment]]
    build_candidates: Callable[..., list[Candidate]]
    score_candidates: Callable[..., list[Candidate]]
    select_candidates: Callable[..., list[Candidate]]
    build_ass: Callable[..., str]
    render_short: Callable[..., Path]


DEFAULT_SERVICES = Services(
    probe_media=probe_media,
    resolve_device=resolve_device,
    detect_scenes=detect_scenes,
    transcribe=transcribe,
    build_candidates=build_candidates,
    score_candidates=score_candidates,
    select_candidates=select_candidates,
    build_ass=build_ass,
    render_short=render_short,
)


def _scene_from_dict(item: dict[str, Any]) -> Scene:
    return Scene(id=int(item["id"]), start=float(item["start"]), end=float(item["end"]))


def _segment_from_dict(item: dict[str, Any]) -> TranscriptSegment:
    return TranscriptSegment(
        start=float(item["start"]),
        end=float(item["end"]),
        text=str(item["text"]),
        words=tuple(WordTiming(**word) for word in item.get("words", [])),
    )


def _candidate_from_dict(item: dict[str, Any]) -> Candidate:
    score = item.get("score")
    return Candidate(
        id=int(item["id"]), start=float(item["start"]), end=float(item["end"]),
        scene_ids=tuple(item["scene_ids"]), text=str(item["text"]),
        score=ScoreBreakdown(**score) if score else None,
    )


class Pipeline:
    def __init__(self, services: Services = DEFAULT_SERVICES) -> None:
        self.services = services

    def run(self, config: RunConfig, progress: Callable[[str], None] | None = None) -> RunReport:
        def notify(message: str) -> None:
            if progress is not None:
                progress(message)

        parameters = asdict(config)
        parameters["input_path"] = str(config.input_path)
        parameters["output_dir"] = str(config.output_dir)
        storage = RunStorage.create(config.output_dir, parameters)
        notify("[1/5] Проверка видео")
        media = self.services.probe_media(config.input_path)
        device = self.services.resolve_device(config.device)
        warnings: list[str] = []
        if config.device == "auto" and device == "cpu":
            warnings.append("CUDA недоступна. Обработка выполняется на CPU.")

        notify("[2/5] Поиск сцен")
        raw_scenes = storage.load_stage("scenes")
        scenes = [_scene_from_dict(item) for item in raw_scenes] if raw_scenes else self.services.detect_scenes(config.input_path, media.duration)
        if raw_scenes is None:
            storage.save_stage("scenes", [asdict(item) for item in scenes])

        notify("[3/5] Расшифровка речи")
        raw_transcript = storage.load_stage("transcript")
        try:
            transcript = [_segment_from_dict(item) for item in raw_transcript] if raw_transcript else self.services.transcribe(config.input_path, config.language, device)
        except UserFacingError:
            storage.log_debug(traceback.format_exc())
            raise
        if raw_transcript is None:
            storage.save_stage("transcript", [asdict(item) for item in transcript])

        raw_candidates = storage.load_stage("candidates")
        if raw_candidates:
            candidates = [_candidate_from_dict(item) for item in raw_candidates]
        else:
            raw_prefiltered = storage.load_stage("prefiltered_candidates")
            if raw_prefiltered:
                candidates = [_candidate_from_dict(item) for item in raw_prefiltered]
            else:
                all_candidates = self.services.build_candidates(
                    scenes,
                    transcript,
                    config.min_duration,
                    config.max_duration,
                    config.skip_intro,
                )
                candidates = prefilter_candidates(all_candidates, config.analysis_limit)
                storage.save_stage("prefiltered_candidates", [asdict(item) for item in candidates])
            notify(f"[4/5] Быстрый отбор: {len(candidates)} кандидатов из {len(all_candidates) if 'all_candidates' in locals() else len(candidates)}")
            candidates = self.services.score_candidates(
                candidates,
                config.input_path,
                media.has_audio,
                progress=lambda current, total: notify(f"[5/5] Точная оценка: {current}/{total}"),
            )
            storage.save_stage("candidates", [asdict(item) for item in candidates])

        selected = self.services.select_candidates(candidates, config.count)
        rendered_files: list[Path] = []
        for index, candidate in enumerate(selected, start=1):
            ass_path = storage.output_dir / "subtitles" / f"short-{index:02d}.ass"
            ass_path.write_text(self.services.build_ass(words_for_interval(transcript, candidate.start, candidate.end), candidate.start), encoding="utf-8")
            target_path = storage.output_dir / "shorts" / f"short-{index:02d}.mp4"
            rendered_files.append(
                self.services.render_short(
                    config.input_path,
                    candidate,
                    ass_path,
                    target_path,
                    storage.output_dir / "logs" / "debug.log",
                )
            )
            if index == 1:
                notify("Создан первый ролик: shorts/short-01.mp4")

        if len(rendered_files) < config.count:
            warnings.append(f"Создано {len(rendered_files)} из {config.count} роликов: подходящих непересекающихся фрагментов недостаточно.")
        return RunReport(rendered_files=tuple(rendered_files), warnings=tuple(warnings))
