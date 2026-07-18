# Movie Shorts CLI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Построить полностью локальную CLI-утилиту, которая из одного русскоязычного фильма создаёт до пяти вертикальных видео с русскими субтитрами.

**Architecture:** Python-пайплайн передаёт между независимыми этапами типизированные модели и сохраняет их JSON-представления в директории запуска. Исходное видео анализируется без предварительной нарезки; финальные временные диапазоны вырезаются и рендерятся только после ранжирования.

**Tech Stack:** Python 3.12, Typer, Pydantic, PySceneDetect, faster-whisper, OpenCV, FFmpeg/ffprobe, pytest.

## Global Constraints

- Весь MVP работает локально и не использует платные API, облачные сервисы, БД или очередь задач.
- Язык первого релиза — `ru`; слой транскрипции должен принимать код языка, чтобы позднее добавить `en` без изменения пайплайна.
- `--device auto` выбирает CUDA, когда она доступна, и иначе использует CPU.
- Пользовательские сообщения и рекомендации CLI выводятся на русском языке; технические детали сторонних программ пишутся в `logs/debug.log`.
- На входе один видеофайл; на выходе до 5 вертикальных MP4 длительностью 20–120 секунд.
- Кандидаты не пересекаются; при недостатке подходящих интервалов программа создаёт меньше запрошенного количества и сообщает причину.
- Исходник не делится на временные видеофайлы до финального рендера.
- Все этапы обновляют `manifest.json`; валидный результат завершённого этапа используется при повторном запуске.

---

## Target file structure

```text
movie-shorts/
  pyproject.toml
  src/movie_shorts/
    __init__.py
    cli.py
    config.py
    errors.py
    models.py
    pipeline.py
    services/
      media.py
      scenes.py
      transcript.py
      candidates.py
      scoring.py
      subtitles.py
      renderer.py
    storage.py
  tests/
    conftest.py
    unit/
    integration/
  docs/superpowers/specs/2026-07-18-movie-shorts-cli-design.md
```

## Task 1: Bootstrap the package and Russian CLI shell

**Files:**
- Create: `pyproject.toml`
- Create: `src/movie_shorts/__init__.py`
- Create: `src/movie_shorts/cli.py`
- Create: `src/movie_shorts/config.py`
- Create: `src/movie_shorts/errors.py`
- Create: `tests/unit/test_cli.py`

**Interfaces:**
- Produces `movie-shorts create INPUT --output OUTPUT` and `RunConfig` for all later tasks.

- [ ] **Step 1: Write failing CLI tests**

```python
from typer.testing import CliRunner
from movie_shorts.cli import app

def test_help_is_in_russian() -> None:
    result = CliRunner().invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "Создать Shorts" in result.output

def test_rejects_non_positive_count(tmp_path) -> None:
    result = CliRunner().invoke(app, ["create", "video.mp4", "--output", str(tmp_path), "--count", "0"])
    assert result.exit_code == 2
    assert "Количество роликов должно быть" in result.output
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `pytest tests/unit/test_cli.py -v`  
Expected: FAIL because `movie_shorts` is not importable.

- [ ] **Step 3: Create the package metadata and minimal CLI**

Use a `src` layout and declare the exact runtime dependencies: `typer>=0.12`, `pydantic>=2.7`, `scenedetect[opencv]>=0.6`, `faster-whisper>=1.0`, `opencv-python-headless>=4.10`. Declare `pytest>=8.0` as a development dependency and `movie-shorts = "movie_shorts.cli:app"` as the console script.

Implement this configuration contract:

```python
@dataclass(frozen=True, slots=True)
class RunConfig:
    input_path: Path
    output_dir: Path
    count: int = 5
    min_duration: float = 20.0
    max_duration: float = 120.0
    language: str = "ru"
    device: Literal["auto", "cpu", "cuda"] = "auto"
```

Validate `count` in `1..5`, positive durations, and `min_duration <= max_duration`. Raise `UserFacingError` with Russian text. The `create` command may print `"Подготовка конвейера…"` and exit successfully at this task; it must not yet process a file.

- [ ] **Step 4: Run the tests and lint importability**

Run: `pytest tests/unit/test_cli.py -v`  
Expected: PASS (2 passed).

Run: `movie-shorts create --help`  
Expected: Russian help text containing `Создать Shorts`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/movie_shorts tests/unit/test_cli.py
git commit -m "feat: bootstrap movie shorts cli"
```

## Task 2: Define domain models and durable run storage

**Files:**
- Create: `src/movie_shorts/models.py`
- Create: `src/movie_shorts/storage.py`
- Create: `tests/unit/test_storage.py`

**Interfaces:**
- Consumes: `RunConfig` from Task 1.
- Produces: `Scene`, `WordTiming`, `TranscriptSegment`, `Candidate`, `ScoreBreakdown`, `RunStorage`.

- [ ] **Step 1: Write failing storage tests**

```python
def test_storage_writes_and_reads_a_completed_stage(tmp_path) -> None:
    storage = RunStorage.create(tmp_path, {"language": "ru"})
    storage.save_stage("scenes", [{"id": 1, "start": 0.0, "end": 3.5}])
    assert storage.load_stage("scenes") == [{"id": 1, "start": 0.0, "end": 3.5}]
    assert storage.manifest()["stages"]["scenes"]["status"] == "completed"

def test_storage_does_not_read_incomplete_stage(tmp_path) -> None:
    storage = RunStorage.create(tmp_path, {})
    assert storage.load_stage("scenes") is None
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `pytest tests/unit/test_storage.py -v`  
Expected: FAIL because `RunStorage` does not exist.

- [ ] **Step 3: Implement immutable models and atomic JSON storage**

Model fields are exactly:

```python
@dataclass(frozen=True, slots=True)
class Scene:
    id: int
    start: float
    end: float

@dataclass(frozen=True, slots=True)
class WordTiming:
    start: float
    end: float
    text: str

@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: tuple[WordTiming, ...]

@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    text: float
    motion: float
    audio: float
    duration: float
    total: float

@dataclass(frozen=True, slots=True)
class Candidate:
    id: int
    start: float
    end: float
    scene_ids: tuple[int, ...]
    text: str
    score: ScoreBreakdown | None = None
```

`RunStorage.create(output_dir, parameters)` creates `logs/`, `shorts/`, `subtitles/` and an initial `manifest.json`. `save_stage(name, payload)` writes `name.json.tmp`, replaces it atomically with `name.json`, then marks the stage `completed` in the manifest. `load_stage(name)` returns `None` unless both the manifest status is `completed` and `name.json` contains valid JSON. Store exception tracebacks only in `logs/debug.log`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_storage.py -v`  
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/models.py src/movie_shorts/storage.py tests/unit/test_storage.py
git commit -m "feat: add pipeline models and run storage"
```

## Task 3: Validate source media and resolve CPU/CUDA device

**Files:**
- Create: `src/movie_shorts/services/media.py`
- Create: `tests/unit/test_media.py`

**Interfaces:**
- Produces `MediaInfo(duration: float, has_video: bool, has_audio: bool)` and `resolve_device(requested: str) -> str`.
- `Pipeline` in Task 10 calls `probe_media(input_path)` before other stages.

- [ ] **Step 1: Write failing tests using mocked subprocess output**

```python
def test_probe_reads_duration_and_streams(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("subprocess.run", fake_ffprobe_success)
    info = probe_media(tmp_path / "film.mp4")
    assert info.duration == 95.4
    assert info.has_video is True
    assert info.has_audio is True

def test_auto_falls_back_to_cpu_when_cuda_is_not_available(monkeypatch) -> None:
    monkeypatch.setattr("movie_shorts.services.media.cuda_available", lambda: False)
    assert resolve_device("auto") == "cpu"
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `pytest tests/unit/test_media.py -v`  
Expected: FAIL because the media service does not exist.

- [ ] **Step 3: Implement ffprobe wrapper and device selection**

Call `ffprobe -v error -show_entries format=duration:stream=codec_type -of json <path>` with `subprocess.run(..., capture_output=True, text=True, check=False)`. Reject missing files, missing video streams, zero/invalid duration and absent `ffprobe` with Russian `UserFacingError` messages. Audio is optional for validation but its absence must be recorded so the audio scorer returns 0 later. `cuda_available()` may use `ctranslate2.get_supported_compute_types("cuda")`, catching all import/runtime errors and returning `False`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_media.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/media.py tests/unit/test_media.py
git commit -m "feat: validate input media and choose device"
```

## Task 4: Detect visual scenes without generating temporary clips

**Files:**
- Create: `src/movie_shorts/services/scenes.py`
- Create: `tests/unit/test_scenes.py`

**Interfaces:**
- Produces `detect_scenes(video_path: Path) -> list[Scene]`.
- Consumes `Scene` from Task 2; Task 6 receives its ordered result.

- [ ] **Step 1: Write failing scene conversion tests**

```python
def test_detector_converts_timecodes_to_ordered_scenes(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("movie_shorts.services.scenes.detect", fake_detect)
    scenes = detect_scenes(tmp_path / "film.mp4", duration=9.0)
    assert scenes == [Scene(id=1, start=0.0, end=4.2), Scene(id=2, start=4.2, end=9.0)]
```

- [ ] **Step 2: Run the test and verify failure**

Run: `pytest tests/unit/test_scenes.py -v`  
Expected: FAIL because `detect_scenes` does not exist.

- [ ] **Step 3: Implement detector adapter**

Use `scenedetect.detect(video_path, ContentDetector())`. Convert scene start/end timecodes to seconds, discard non-positive intervals, sort by start, and assign IDs beginning at 1. If no cuts are found, return one scene covering the media duration supplied to the adapter; therefore give the function signature `detect_scenes(video_path: Path, duration: float) -> list[Scene]`. Do not call FFmpeg and do not create scene video files.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_scenes.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/scenes.py tests/unit/test_scenes.py
git commit -m "feat: detect visual scene boundaries"
```

## Task 5: Transcribe the full movie once with Russian word timestamps

**Files:**
- Create: `src/movie_shorts/services/transcript.py`
- Create: `tests/unit/test_transcript.py`

**Interfaces:**
- Produces `transcribe(video_path: Path, language: str, device: str) -> list[TranscriptSegment]`.
- Task 6 filters the returned segments and words by candidate timestamps.

- [ ] **Step 1: Write failing adapter tests with a fake Whisper model**

```python
def test_transcriber_preserves_words_and_language(monkeypatch, tmp_path) -> None:
    factory = FakeModelFactory()
    monkeypatch.setattr("movie_shorts.services.transcript.WhisperModel", factory)
    segments = transcribe(tmp_path / "film.mp4", language="ru", device="cpu")
    assert factory.calls[0]["device"] == "cpu"
    assert segments[0].words[0] == WordTiming(start=0.1, end=0.4, text="Привет")
```

- [ ] **Step 2: Run test and verify failure**

Run: `pytest tests/unit/test_transcript.py -v`  
Expected: FAIL because the transcript adapter does not exist.

- [ ] **Step 3: Implement the faster-whisper adapter**

Instantiate `WhisperModel("small", device=device, compute_type="float16" if device == "cuda" else "int8")`. Call `model.transcribe(str(video_path), language=language, word_timestamps=True, vad_filter=True)`. Convert all returned segments and words into the Task 2 models. Convert model/download/runtime failures to `UserFacingError("Не удалось распознать речь в видео. Подробности сохранены в logs/debug.log.")`; log the original exception in the pipeline layer. Empty speech is valid and returns an empty list.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_transcript.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/transcript.py tests/unit/test_transcript.py
git commit -m "feat: add full-video russian transcription"
```

## Task 6: Build candidate intervals and attach their transcript text

**Files:**
- Create: `src/movie_shorts/services/candidates.py`
- Create: `tests/unit/test_candidates.py`

**Interfaces:**
- Consumes: `list[Scene]`, `list[TranscriptSegment]`, `min_duration`, `max_duration`.
- Produces `build_candidates(...) -> list[Candidate]` and `words_for_interval(...) -> tuple[WordTiming, ...]`.

- [ ] **Step 1: Write failing candidate tests**

```python
def test_builder_merges_adjacent_scenes_until_minimum_duration() -> None:
    scenes = [Scene(1, 0, 8), Scene(2, 8, 17), Scene(3, 17, 28)]
    candidates = build_candidates(scenes, [], min_duration=20, max_duration=120)
    assert candidates[0].start == 0
    assert candidates[0].end == 28
    assert candidates[0].scene_ids == (1, 2, 3)

def test_builder_never_returns_interval_longer_than_maximum() -> None:
    scenes = [Scene(1, 0, 70), Scene(2, 70, 140)]
    assert all(candidate.end - candidate.start <= 120 for candidate in build_candidates(scenes, [], 20, 120))
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/unit/test_candidates.py -v`  
Expected: FAIL because candidate functions do not exist.

- [ ] **Step 3: Implement deterministic sliding scene windows**

For every starting scene, append consecutive scenes until duration is at least `min_duration`; retain the interval only if it is no longer than `max_duration`. Continue appending scenes while the max duration is respected, emitting each qualifying window. De-duplicate exact `(start, end)` windows and give stable IDs ordered by `(start, end)`. Attach text made from words that overlap `[start, end]`; if word timing is unavailable, use overlapping segment text. Do not discard speechless candidates here—later scoring decides their rank.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_candidates.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/candidates.py tests/unit/test_candidates.py
git commit -m "feat: build timed short candidates"
```

## Task 7: Implement transparent text, motion, audio, and duration scoring

**Files:**
- Create: `src/movie_shorts/services/scoring.py`
- Create: `tests/unit/test_scoring.py`

**Interfaces:**
- Consumes: `Candidate`, source path, optional audio flag.
- Produces `score_candidates(candidates, video_path, has_audio) -> list[Candidate]` with non-null `ScoreBreakdown`.

- [ ] **Step 1: Write failing deterministic scoring tests**

```python
def test_text_score_is_case_insensitive_for_russian_keywords() -> None:
    assert keyword_score("Беги! Там монстр.", {"беги": 18, "монстр": 25}) == 43

def test_duration_score_prefers_35_to_75_seconds() -> None:
    assert duration_score(50) > duration_score(20)
    assert duration_score(50) > duration_score(115)

def test_selector_score_breakdown_has_weighted_total(monkeypatch, tmp_path) -> None:
    candidate = Candidate(1, 0, 50, (1,), "беги")
    scored = score_candidates([candidate], tmp_path / "x.mp4", has_audio=False)
    assert scored[0].score is not None
    assert 0 <= scored[0].score.total <= 100
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/unit/test_scoring.py -v`  
Expected: FAIL because scorer functions do not exist.

- [ ] **Step 3: Implement scores and fixed default weights**

Use the default Russian keyword dictionary `{ "убей": 20, "смерть": 20, "беги": 18, "помогите": 15, "монстр": 25, "кровь": 25, "пистолет": 18, "спасайся": 18 }`; tokenize with lowercase Unicode words. Sample video frames at 2 FPS using OpenCV and compute motion as the mean grayscale `absdiff` between adjacent sampled frames. Run `ffmpeg -af astats=metadata=1:reset=1 -f null -` on the candidate interval and derive audio score from parsed peak and RMS values; missing audio or command failure yields 0 and logs a debug warning. Duration score is 100 for 35–75 seconds, linearly falls toward 0 at 20 and 120 seconds.

Normalize raw text, motion and audio values among all candidates to 0–100; if a metric is equal for every candidate, use 0 for it. Calculate `total = text*0.30 + motion*0.25 + audio*0.20 + duration*0.25`; keep all components rounded to two decimals. The duration weight is 0.25 because face detection is explicitly out of MVP; document it in `candidates.json`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_scoring.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/scoring.py tests/unit/test_scoring.py
git commit -m "feat: score candidates with local media signals"
```

## Task 8: Select non-overlapping winners and build ASS subtitles

**Files:**
- Create: `src/movie_shorts/services/subtitles.py`
- Modify: `src/movie_shorts/services/candidates.py`
- Create: `tests/unit/test_selection.py`
- Create: `tests/unit/test_subtitles.py`

**Interfaces:**
- Produces `select_candidates(candidates, count) -> list[Candidate]` and `build_ass(words, video_start) -> str`.
- Task 10 gives each selected candidate's words to `SubtitleBuilder`.

- [ ] **Step 1: Write failing selection and subtitle tests**

```python
def test_selection_keeps_highest_scored_non_overlapping_candidates() -> None:
    selected = select_candidates([scored(1, 0, 50, 90), scored(2, 40, 80, 99), scored(3, 81, 110, 80)], 2)
    assert [item.id for item in selected] == [2, 3]

def test_ass_contains_russian_style_and_relative_timestamps() -> None:
    ass = build_ass((WordTiming(10.0, 10.5, "Привет"),), video_start=10.0)
    assert "PlayResY:1920" in ass
    assert "0:00:00.00" in ass
    assert "Привет" in ass
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/unit/test_selection.py tests/unit/test_subtitles.py -v`  
Expected: FAIL because selection/subtitle functions do not exist.

- [ ] **Step 3: Implement greedy selection and ASS writer**

Sort candidates by descending total, then ascending start and ID. Add a candidate only when it does not overlap any selected interval using `candidate.start < selected.end and selected.start < candidate.end`; stop at `count`, then sort selected by score rank for deterministic names `short-01` etc.

Create valid ASS with `PlayResX:1080`, `PlayResY:1920`, a large Arial style, black outline and bottom alignment. Convert absolute word times into times relative to `video_start`. For each word create one dialogue line with `\\k` karaoke timing and yellow `\\c&H00FFFF&` current-word colour; when `words` is empty, return a valid header with no dialogue events. Escape `{`, `}`, and backslashes in transcript text.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_selection.py tests/unit/test_subtitles.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/candidates.py src/movie_shorts/services/subtitles.py tests/unit/test_selection.py tests/unit/test_subtitles.py
git commit -m "feat: select winners and create ass subtitles"
```

## Task 9: Render safe vertical MP4 output with FFmpeg

**Files:**
- Create: `src/movie_shorts/services/renderer.py`
- Create: `tests/integration/test_renderer.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Consumes `Candidate`, source path, `.ass` subtitle path and target `.mp4` path.
- Produces `render_short(...) -> Path`.

- [ ] **Step 1: Write an FFmpeg-backed integration test**

```python
@pytest.mark.integration
def test_renderer_creates_vertical_mp4_with_audio(tmp_path, sample_video) -> None:
    output = render_short(sample_video, Candidate(1, 0, 2, (1,), ""), None, tmp_path / "out.mp4")
    info = probe_media(output)
    assert output.exists()
    assert info.has_video is True
    assert read_video_dimensions(output) == (1080, 1920)
```

`sample_video` must use FFmpeg during fixture setup to create a two-second colour video with sine-wave audio. Skip this test only when FFmpeg is not installed, with an explicit skip reason.

- [ ] **Step 2: Run test and verify failure**

Run: `pytest tests/integration/test_renderer.py -v`  
Expected: FAIL because renderer does not exist.

- [ ] **Step 3: Implement one-pass final render**

Call FFmpeg with `-ss <candidate.start>` before `-i`, `-t <duration>`, H.264 video, AAC audio and a filter chain that scales a blurred copy to 1080x1920 then overlays a centered, aspect-preserved foreground. Add the ASS filter only when a subtitle file was generated. Write to `<target>.tmp.mp4`; after zero exit status, call `probe_media` and ensure the final duration is positive, then atomically rename to the target. On FFmpeg error delete only this known temporary file, log stderr, and raise `UserFacingError("Не удалось создать итоговый ролик. Подробности сохранены в logs/debug.log.")`.

- [ ] **Step 4: Run integration test**

Run: `pytest tests/integration/test_renderer.py -v`  
Expected: PASS when FFmpeg is installed; otherwise SKIPPED with the stated reason.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/renderer.py tests/conftest.py tests/integration/test_renderer.py
git commit -m "feat: render vertical short videos"
```

## Task 10: Orchestrate resumable pipeline and user-facing reporting

**Files:**
- Create: `src/movie_shorts/pipeline.py`
- Modify: `src/movie_shorts/cli.py`
- Create: `tests/unit/test_pipeline.py`

**Interfaces:**
- Consumes all previous services and `RunConfig`.
- Produces `Pipeline.run(config: RunConfig) -> RunReport`, where `RunReport.rendered_files: tuple[Path, ...]` and `RunReport.warnings: tuple[str, ...]`.

- [ ] **Step 1: Write failing orchestration tests using fake services**

```python
def test_pipeline_reuses_completed_scenes_stage(tmp_path, fake_services) -> None:
    storage = RunStorage.create(tmp_path, {})
    storage.save_stage("scenes", [{"id": 1, "start": 0, "end": 25}])
    report = Pipeline(fake_services).run(config_for(tmp_path))
    assert fake_services.scene_detector.calls == 0
    assert report.rendered_files

def test_pipeline_reports_fewer_candidates_in_russian(tmp_path, fake_services) -> None:
    report = Pipeline(fake_services.with_one_candidate()).run(config_for(tmp_path, count=5))
    assert "Создано 1 из 5 роликов" in report.warnings[0]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/unit/test_pipeline.py -v`  
Expected: FAIL because `Pipeline` does not exist.

- [ ] **Step 3: Implement stage orchestration**

Run stages in this order: media validation, scene detection, transcription, candidate construction, scoring, selection, ASS generation, rendering. Serialize and restore the exact Task 2 models at each persisted boundary. Mark a stage `running` before work and `failed` with a Russian public message after a handled error. Log full tracebacks in `debug.log`. Continue rendering remaining selected candidates if one render fails, then return a report containing generated paths and per-candidate Russian warnings. In `cli.py`, catch `UserFacingError`, print its message to stderr, and use exit code 1; use exit code 0 when at least one MP4 was created.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_pipeline.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/pipeline.py src/movie_shorts/cli.py tests/unit/test_pipeline.py
git commit -m "feat: orchestrate resumable shorts pipeline"
```

## Task 11: Add configuration, user documentation, and end-to-end acceptance checks

**Files:**
- Create: `config.example.yaml`
- Create: `README.md`
- Create: `tests/integration/test_cli_e2e.py`
- Create: `tests/unit/test_config.py`
- Modify: `src/movie_shorts/config.py`

**Interfaces:**
- Produces optional `--config config.yaml`; command options override YAML values.
- Documents installation, FFmpeg prerequisites, CPU/CUDA modes, input/output and Russian errors.

- [ ] **Step 1: Write failing config precedence and E2E tests**

```python
def test_cli_options_override_yaml_values(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("count: 3\nmin_duration: 30\n", encoding="utf-8")
    config = load_run_config("film.mp4", tmp_path / "out", config_path, count=5)
    assert config.count == 5
    assert config.min_duration == 30
```

The E2E test must create a 25-second Russian-audio fixture or use mocked `Transcriber` output; invoke the CLI and assert `manifest.json`, `scenes.json`, `transcript.json`, `candidates.json`, `.ass`, `.mp4`, and Russian completion text exist. It must not download a Whisper model in CI.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/integration/test_cli_e2e.py tests/unit/test_config.py -v`  
Expected: FAIL because YAML configuration support does not exist.

- [ ] **Step 3: Implement configuration and documentation**

Add `pyyaml>=6.0` to dependencies. Support `count`, `min_duration`, `max_duration`, `language`, `device`, `keywords` and `weights` in YAML. Reject unknown values and invalid weights with Russian errors. Provide `config.example.yaml` with the default Russian keywords and weights from Task 7. README must include exact installation commands, the external FFmpeg requirement, sample CPU and CUDA commands, output tree, configuration precedence, expected processing costs, legal/copyright caution, and troubleshooting messages in Russian.

- [ ] **Step 4: Run full verification**

Run: `pytest -v`  
Expected: all unit tests PASS; FFmpeg integration tests PASS or are explicitly SKIPPED only when FFmpeg is unavailable.

Run: `movie-shorts create --help`  
Expected: Russian help with all user options, including `--config`.

- [ ] **Step 5: Commit**

```bash
git add config.example.yaml README.md src/movie_shorts/config.py tests/integration/test_cli_e2e.py tests/unit/test_config.py pyproject.toml
git commit -m "docs: document local movie shorts workflow"
```

## Final acceptance checklist

- [ ] On a CPU-only machine, a Russian video produces at least one valid 1080x1920 MP4 and ASS subtitles.
- [ ] On a CUDA-capable machine, `--device auto` chooses CUDA; CPU is used with a Russian warning when CUDA is absent.
- [ ] A configured run returns no more than five non-overlapping candidates, each within 20–120 seconds.
- [ ] A second identical run reuses completed JSON stage data and retains the same selected timestamps.
- [ ] Invalid input, FFmpeg failure, CUDA absence, and Whisper failure produce actionable Russian CLI text and preserve technical diagnostics in `logs/debug.log`.
- [ ] `candidates.json` explains the component scores and total score for every candidate.
