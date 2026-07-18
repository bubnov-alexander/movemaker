# Adaptive Background Music Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render every generated short with a locally supplied adaptive background track, using YA YA for epic fragments and keeping music below original audio.

**Architecture:** `RunConfig` exposes an optional immutable `BackgroundMusicConfig`. A music service deterministically selects either epic or calm music from the candidate's existing text, motion, audio and aggregate scores. The pipeline persists that choice; the renderer loops/trims the track and sidechain-ducks it against source audio.

**Tech Stack:** Python 3.12, dataclasses, PyYAML, pytest, FFmpeg (`atrim`, `sidechaincompress`, `amix`).

## Global Constraints

- Tracks remain local user-supplied files; do not download or add music files to Git.
- `FindMyName - YA YA` is epic; `altyn - tatarka slowed (instrumental)` is calm.
- Without music configuration, rendering retains the existing source-audio-only command path.
- Original audio is never attenuated by this feature.
- All new user-facing errors are in Russian.

## File structure

- Modify `src/movie_shorts/config.py`: optional music configuration.
- Create `src/movie_shorts/services/music.py`: epic score and deterministic selection.
- Modify `src/movie_shorts/services/renderer.py`: adaptive FFmpeg graph.
- Modify `src/movie_shorts/pipeline.py` and `src/movie_shorts/storage.py`: selection and manifest data.
- Modify `config.example.yaml`, `README.md`, and tests in `tests/unit` / `tests/integration`.

### Task 1: Parse and validate the music configuration

**Files:**
- Modify: `src/movie_shorts/config.py`
- Modify: `config.example.yaml`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Produce `BackgroundMusicConfig(epic_path: Path, calm_path: Path, max_volume: float = 0.12, quiet_volume: float = 0.18, epic_threshold: float = 60.0)`.
- Add `RunConfig.background_music: BackgroundMusicConfig | None`.

- [ ] **Step 1: Write the failing test**

```python
def test_reads_background_music_from_yaml(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "background_music:\n  epic_path: music/yaya.mp3\n  calm_path: music/altyn.mp3\n"
        "  max_volume: 0.1\n  quiet_volume: 0.16\n  epic_threshold: 55\n",
        encoding="utf-8",
    )

    config = load_run_config("film.mp4", tmp_path / "out", config_path)

    assert config.background_music == BackgroundMusicConfig(
        Path("music/yaya.mp3"), Path("music/altyn.mp3"), 0.1, 0.16, 55
    )
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/test_config.py::test_reads_background_music_from_yaml -v`  
Expected: FAIL because `BackgroundMusicConfig` is missing.

- [ ] **Step 3: Implement the minimal parser**

Create a frozen/slotted dataclass and validate `0 < max_volume <= quiet_volume <= 1` and `0 <= epic_threshold <= 100`. Add `background_music` to the accepted YAML keys. It must be a mapping with both paths; otherwise raise the Russian `UserFacingError`. Construct the dataclass only when the section exists. Add this documented configuration:

```yaml
background_music:
  epic_path: music/yaya.mp3
  calm_path: music/altyn.mp3
  max_volume: 0.12
  quiet_volume: 0.18
  epic_threshold: 60
```

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/unit/test_config.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/config.py config.example.yaml tests/unit/test_config.py
git commit -m "feat: добавить конфигурацию фоновой музыки"
```

### Task 2: Select an epic or calm track

**Files:**
- Create: `src/movie_shorts/services/music.py`
- Test: `tests/unit/test_music.py`

**Interfaces:**
- Produce `MusicSelection(track: Literal["epic", "calm"], path: Path, epic_score: float)`.
- Produce `select_background_music(candidate: Candidate, config: BackgroundMusicConfig) -> MusicSelection`.

- [ ] **Step 1: Write failing tests**

```python
def test_selects_epic_track_when_all_signals_are_high() -> None:
    candidate = Candidate(1, 0, 30, (), "беги монстр", ScoreBreakdown(90, 80, 70, 100, 85))

    selection = select_background_music(candidate, music_config(epic_threshold=60))

    assert selection.track == "epic"
    assert selection.path == Path("music/yaya.mp3")

def test_selects_calm_track_for_low_energy_dialogue() -> None:
    candidate = Candidate(1, 0, 30, (), "давай поговорим", ScoreBreakdown(5, 10, 10, 100, 25))

    assert select_background_music(candidate, music_config()).track == "calm"
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/test_music.py -v`  
Expected: FAIL because the music service is absent.

- [ ] **Step 3: Implement deterministic selection**

```python
def epic_score(candidate: Candidate) -> float:
    score = candidate.score
    if score is None:
        return 0.0
    return round(score.text * .35 + score.motion * .30 + score.audio * .20 + score.total * .15, 2)

def select_background_music(candidate: Candidate, config: BackgroundMusicConfig) -> MusicSelection:
    score = epic_score(candidate)
    if score >= config.epic_threshold:
        return MusicSelection("epic", config.epic_path, score)
    return MusicSelection("calm", config.calm_path, score)
```

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/unit/test_music.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/music.py tests/unit/test_music.py
git commit -m "feat: выбирать фоновый трек по сцене"
```

### Task 3: Render looped music with automatic ducking

**Files:**
- Modify: `src/movie_shorts/services/renderer.py`
- Modify: `tests/unit/test_renderer.py`
- Modify: `tests/integration/test_ffmpeg_renderer.py`

**Interfaces:**
- Extend `render_command` and `render_short` with optional `music: MusicSelection | None` and `music_config: BackgroundMusicConfig | None`.

- [ ] **Step 1: Write failing command and FFmpeg integration tests**

```python
def test_render_command_ducks_looped_background_music() -> None:
    command = render_command(Path("film.mp4"), Candidate(7, 10, 30, (), ""), None,
                             Path("out.mp4"), epic_selection, music_config)
    rendered = " ".join(command)

    assert command.count("-i") == 2
    assert "atrim=duration=20" in rendered
    assert "sidechaincompress" in rendered
    assert "[mixed]" in rendered
```

Generate a separate sine-wave MP3 in the integration test, render a two-second fixture with it, then use `ffprobe` to assert that output has an audio stream.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/test_renderer.py tests/integration/test_ffmpeg_renderer.py -v`  
Expected: FAIL because the renderer does not accept a music selection.

- [ ] **Step 3: Implement the optional graph**

Use `-stream_loop -1 -i <track>`; reject a missing path with `UserFacingError(f"Не найден фоновый трек: {music.path}")`. For sources with audio, append:

```text
[1:a]volume={quiet_volume},atrim=duration={duration},asetpts=N/SR/TB[music];
[0:a]asplit=2[original][sidechain];
[music][sidechain]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[ducked];
[ducked]volume={max_volume / quiet_volume}[music_limited];
[original][music_limited]amix=inputs=2:duration=first:normalize=0[mixed]
```

Map `[mixed]`. When source audio is missing, map the trimmed, volume-limited music stream. When music is disabled, retain existing `-map 0:a?` behavior.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/unit/test_renderer.py tests/integration/test_ffmpeg_renderer.py -v`  
Expected: PASS; integration is skipped only if FFmpeg is unavailable.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/renderer.py tests/unit/test_renderer.py tests/integration/test_ffmpeg_renderer.py
git commit -m "feat: подмешивать музыку с ducking"
```

### Task 4: Wire selection into the pipeline and make it inspectable

**Files:**
- Modify: `src/movie_shorts/pipeline.py`
- Modify: `src/movie_shorts/storage.py`
- Modify: `tests/unit/test_pipeline.py`
- Modify: `README.md`

**Interfaces:**
- Add `RunStorage.save_short_metadata(index: int, candidate_id: int, music: MusicSelection | None) -> None`.
- Pass the selection/configuration to the renderer service callable.

- [ ] **Step 1: Write a failing pipeline test**

```python
def test_pipeline_records_and_passes_selected_music(tmp_path) -> None:
    received = []
    services = make_services(render_short=lambda *args: received.append(args[4]) or tmp_path / "short.mp4")

    Pipeline(services).run(RunConfig(source, tmp_path / "out", background_music=music_config()))

    assert received[0].track == "epic"
    metadata = RunStorage(tmp_path / "out").manifest()["shorts"]["short-01"]["music"]
    assert metadata["track"] == "epic"
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/test_pipeline.py::test_pipeline_records_and_passes_selected_music -v`  
Expected: FAIL because no selection is passed or recorded.

- [ ] **Step 3: Implement the boundary**

Select music per candidate only if `config.background_music` exists, then record track, path, and epic score under `manifest["shorts"]["short-XX"]["music"]`. Pass selection/config to `render_short`. Use null music metadata when disabled. Update fake callable signatures.

Add a README section instructing the user to copy the two tracks into untracked `music/`, configure their paths, and tune volume/threshold. State that YA YA is selected by text, motion, audio energy, and aggregate score, and that original audio ducks the music.

- [ ] **Step 4: Run full verification**

Run: `pytest -v`  
Expected: PASS, with only FFmpeg-dependent tests skipped when FFmpeg is absent.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/pipeline.py src/movie_shorts/storage.py tests/unit/test_pipeline.py README.md
git commit -m "feat: подключить адаптивную музыку в pipeline"
```

