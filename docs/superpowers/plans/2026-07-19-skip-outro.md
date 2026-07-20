# Skip Outro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude the last 60 seconds of a video from short selection by default and expose the value through YAML and `--skip-outro`.

**Architecture:** Add a defaulted `RunConfig.skip_outro`, forward it from the CLI/config parser into candidate construction, and use the known source duration to reject intervals ending in the excluded tail.

**Tech Stack:** Python 3.12, Typer, PyYAML, pytest.

## Global Constraints

- `skip_outro` defaults to exactly 60 seconds.
- CLI `--skip-outro` overrides YAML.
- Zero disables exclusion; negative values produce a Russian user-facing error.

---

### Task 1: Add configuration and CLI input

**Files:**
- Modify: `src/movie_shorts/config.py`
- Modify: `src/movie_shorts/cli.py`
- Modify: `config.example.yaml`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
def test_skip_outro_defaults_to_sixty_seconds(tmp_path) -> None:
    assert load_run_config("film.mp4", tmp_path / "out").skip_outro == 60

def test_reads_skip_outro_from_yaml(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("skip_outro: 45\n", encoding="utf-8")
    assert load_run_config("film.mp4", tmp_path / "out", path).skip_outro == 45
```

Add a CLI test that invokes `create(..., skip_outro=30)` and asserts the fake pipeline receives `config.skip_outro == 30`.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/unit/test_config.py tests/unit/test_cli.py -v`  
Expected: FAIL because `skip_outro` is not a configuration field or CLI option.

- [ ] **Step 3: Implement minimal input flow**

Add `skip_outro: float = 60.0` to `RunConfig`; reject negatives with `UserFacingError("Длительность пропуска конца не может быть отрицательной.")`. Add it to accepted YAML keys and `load_run_config`. Add Typer option `--skip-outro` and forward it as an override. Document `skip_outro: 60` in `config.example.yaml`.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/unit/test_config.py tests/unit/test_cli.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/config.py src/movie_shorts/cli.py config.example.yaml tests/unit/test_config.py tests/unit/test_cli.py
git commit -m "feat: добавить skip outro в CLI"
```

### Task 2: Apply the outro boundary during candidate generation

**Files:**
- Modify: `src/movie_shorts/services/candidates.py`
- Modify: `src/movie_shorts/pipeline.py`
- Modify: `tests/unit/test_candidates.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing boundary test**

```python
def test_builder_excludes_intervals_that_reach_outro() -> None:
    scenes = [Scene(1, 0, 30), Scene(2, 30, 60), Scene(3, 60, 90)]
    candidates = build_candidates(scenes, [], 20, 60, video_duration=90, skip_outro=45)

    assert all(candidate.end <= 45 for candidate in candidates)
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/pytest tests/unit/test_candidates.py::test_builder_excludes_intervals_that_reach_outro -v`  
Expected: FAIL because `build_candidates` does not accept `video_duration` and `skip_outro`.

- [ ] **Step 3: Implement and wire the limit**

Extend `build_candidates(..., skip_intro=0.0, video_duration: float | None = None, skip_outro: float = 0.0)`. Set `latest_end = video_duration - skip_outro` when duration is given; do not add any interval whose current scene ends after it. Pass `media.duration` and `config.skip_outro` from `Pipeline.run`. Add README examples for both `--skip-outro 60` and YAML.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/pytest tests/unit/test_candidates.py tests/unit/test_pipeline.py -v`  
Expected: PASS.

- [ ] **Step 5: Run full verification and commit**

Run: `.venv/bin/pytest -v`  
Expected: PASS.

```bash
git add src/movie_shorts/services/candidates.py src/movie_shorts/pipeline.py tests/unit/test_candidates.py README.md
git commit -m "feat: исключать outro из кандидатов"
```

