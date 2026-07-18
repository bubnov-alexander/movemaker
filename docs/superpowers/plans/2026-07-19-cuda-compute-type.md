# CUDA Compute Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Автоматически выбрать поддерживаемый тип вычислений CTranslate2 для CUDA.

**Architecture:** `transcript.py` получает маленькую функцию выбора режима и использует её при создании `WhisperModel`. Внешний интерфейс `transcribe` остаётся неизменным.

**Tech Stack:** Python 3.12, faster-whisper, CTranslate2, pytest.

## Global Constraints

- Сообщения об ошибках остаются на русском.
- На CPU используется `int8`.
- Для CUDA приоритет: `float16`, `int8_float16`, `int8_float32`, `int8`, `float32`.

---

### Task 1: Выбор доступного типа CUDA

**Files:**
- Modify: `src/movie_shorts/services/transcript.py`
- Modify: `tests/unit/test_transcript.py`

**Interfaces:**
- Produces: `_compute_type(device: str, supported_cuda_types: set[str] | None = None) -> str`
- Consumes: `transcribe(video_path: Path, language: str, device: str) -> list[TranscriptSegment]`

- [x] **Step 1: Write the failing test**

```python
def test_transcriber_uses_supported_cuda_compute_type(monkeypatch, tmp_path) -> None:
    factory = FakeModelFactory()
    monkeypatch.setattr("movie_shorts.services.transcript.WhisperModel", factory)
    monkeypatch.setattr(
        "movie_shorts.services.transcript.ctranslate2.get_supported_compute_types",
        lambda device: {"int8", "float32", "int8_float32"},
    )

    transcribe(tmp_path / "film.mp4", language="ru", device="cuda")

    assert factory.calls[0]["compute_type"] == "int8_float32"
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_transcript.py::test_transcriber_uses_supported_cuda_compute_type -v`

Expected: FAIL because the implementation requests `float16`.

- [x] **Step 3: Write minimal implementation**

```python
def _compute_type(device: str) -> str:
    if device != "cuda":
        return "int8"
    supported = ctranslate2.get_supported_compute_types("cuda")
    for compute_type in ("float16", "int8_float16", "int8_float32", "int8", "float32"):
        if compute_type in supported:
            return compute_type
    return "float32"
```

Pass `_compute_type(device)` as `compute_type` to `WhisperModel`.

- [x] **Step 4: Run tests to verify the change**

Run: `.venv/bin/pytest tests/unit/test_transcript.py -v && .venv/bin/pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Commit and publish**

```bash
git add src/movie_shorts/services/transcript.py tests/unit/test_transcript.py docs/superpowers
git commit -m "fix: выбирать поддерживаемый режим cuda"
git push origin master
```
