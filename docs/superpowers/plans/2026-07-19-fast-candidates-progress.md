# Fast Candidates and CLI Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ограничить тяжёлую оценку кандидатов, показать реальный прогресс CLI и создавать первый ролик без многочасового ожидания.

**Architecture:** После расшифровки быстрый ранжировщик сортирует все интервалы по тексту и длительности, сохраняет ограниченный набор в `prefiltered_candidates.json` и передаёт только его тяжёлому анализатору. `Pipeline` получает callback прогресса, а CLI печатает его в stderr и перехватывает пользовательские ошибки всего запуска.

**Tech Stack:** Python 3.12, Typer, dataclasses, FFmpeg, OpenCV, pytest.

## Global Constraints

- Значение `analysis_limit` по умолчанию равно 30 и является положительным целым числом.
- Метрики движения и звука не вычисляются более чем для `analysis_limit` кандидатов.
- CLI печатает русскоязычный прогресс только после реально выполненных действий.
- Ошибки конвейера выводятся одной русской строкой без traceback.
- Существующие `scenes.json` и `transcript.json` повторно используются без новой обработки.

---

### Task 1: Fast prefilter and bounded precise scoring

**Files:**
- Modify: `src/movie_shorts/config.py`
- Modify: `src/movie_shorts/services/scoring.py`
- Modify: `src/movie_shorts/pipeline.py`
- Modify: `tests/unit/test_scoring.py`
- Modify: `tests/unit/test_pipeline.py`

**Interfaces:**
- Produces `RunConfig.analysis_limit: int = 30`.
- Produces `prefilter_candidates(candidates: list[Candidate], limit: int) -> list[Candidate]`.
- `Pipeline.run` persists `prefiltered_candidates.json` before calling `score_candidates`.

- [ ] **Step 1: Write failing tests**

```python
def test_prefilter_limits_candidates_by_text_and_duration() -> None:
    candidates = [Candidate(1, 0, 50, (), "беги монстр"), Candidate(2, 60, 110, (), "")]
    assert [item.id for item in prefilter_candidates(candidates, limit=1)] == [1]

def test_pipeline_passes_only_analysis_limit_to_precise_scorer(tmp_path, fake_services) -> None:
    report = Pipeline(fake_services.with_candidates(40)).run(config_for(tmp_path, analysis_limit=3))
    assert fake_services.score_candidates.received_count == 3
```

- [ ] **Step 2: Verify failing tests**

Run: `.venv/bin/python -m pytest tests/unit/test_scoring.py tests/unit/test_pipeline.py -v`  
Expected: FAIL because `analysis_limit` and `prefilter_candidates` do not exist.

- [ ] **Step 3: Implement the bounded path**

Add `analysis_limit` to `RunConfig`, YAML allow-list and CLI configuration loading. Reject `analysis_limit < 1` with `UserFacingError("Лимит анализа должен быть больше нуля.")`.

Implement `prefilter_candidates` using `keyword_score(candidate.text)` and `duration_score(candidate.end - candidate.start)`. Sort by descending combined score, then ascending start and ID; return at most `limit` entries. In `Pipeline`, persist the selected candidates in `prefiltered_candidates.json`; on later runs restore it before precise scoring. Call `score_candidates` only with this list.

- [ ] **Step 4: Verify passing tests**

Run: `.venv/bin/python -m pytest tests/unit/test_scoring.py tests/unit/test_pipeline.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/config.py src/movie_shorts/services/scoring.py src/movie_shorts/pipeline.py tests/unit/test_scoring.py tests/unit/test_pipeline.py
git commit -m "feat: limit precise candidate analysis"
```

### Task 2: Progress reporting, first clip, and user-facing errors

**Files:**
- Modify: `src/movie_shorts/pipeline.py`
- Modify: `src/movie_shorts/cli.py`
- Modify: `tests/unit/test_cli.py`
- Modify: `tests/unit/test_pipeline.py`
- Modify: `README.md`
- Modify: `config.example.yaml`

**Interfaces:**
- `Pipeline.run(config: RunConfig, progress: Callable[[str], None] | None = None) -> RunReport`.
- `progress` receives completed-stage strings, including `"[5/5] Точная оценка: {current}/{total}"`.

- [ ] **Step 1: Write failing tests**

```python
def test_pipeline_reports_precise_scoring_progress(tmp_path, fake_services) -> None:
    messages = []
    Pipeline(fake_services.with_candidates(2)).run(config_for(tmp_path), progress=messages.append)
    assert "[5/5] Точная оценка: 2/2" in messages

def test_cli_prints_user_error_without_traceback(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("movie_shorts.cli.Pipeline.run", lambda *_: (_ for _ in ()).throw(UserFacingError("Файл не найден.")))
    result = CliRunner().invoke(app, ["create", "missing.mp4", "--output", str(tmp_path)])
    assert result.exit_code == 1
    assert result.output == "Файл не найден.\n"
```

- [ ] **Step 2: Verify failing tests**

Run: `.venv/bin/python -m pytest tests/unit/test_cli.py tests/unit/test_pipeline.py -v`  
Expected: FAIL because `Pipeline.run` has no progress callback and CLI does not catch its `UserFacingError`.

- [ ] **Step 3: Implement progress and safe CLI handling**

Call progress after checking media, detecting/loading scenes, detecting/loading transcript, prefiltering, and after each precise-scoring candidate. Print progress via `typer.echo(message, err=True)`. Catch `UserFacingError` around the `Pipeline().run(...)` invocation, print only its message to stderr and exit with code 1.

Render the selected first candidate before iterating through the remaining candidates. After its successful render call progress with `Создан первый ролик: shorts/short-01.mp4`.

Add `analysis_limit: 30` to the example YAML and document the setting, progress messages, and CPU trade-off in README.

- [ ] **Step 4: Verify passing tests and full regression suite**

Run: `.venv/bin/python -m pytest -v`  
Expected: PASS, with the FFmpeg integration test either PASS or SKIPPED only when FFmpeg is unavailable.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/pipeline.py src/movie_shorts/cli.py tests/unit/test_cli.py tests/unit/test_pipeline.py README.md config.example.yaml
git commit -m "feat: report pipeline progress"
```
