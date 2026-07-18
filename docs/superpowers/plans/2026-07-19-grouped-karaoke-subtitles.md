# Grouped Karaoke Subtitles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Показывать в ASS-субтитрах короткие фразы вместо одного слова, подсвечивая текущее слово жёлтым цветом.

**Architecture:** `build_ass` сначала группирует последовательные `WordTiming` в фразы по числу слов, паузе и длительности. Затем каждая группа превращается в одну ASS dialogue-строку с karaoke-тегами для слов.

**Tech Stack:** Python 3.12, ASS subtitles, pytest.

## Global Constraints

- В одной фразе максимум четыре слова.
- Пауза больше 0,45 секунды и длительность больше 2,5 секунды завершают фразу.
- Расшифровка не запускается повторно: используются текущие `WordTiming`.

---

### Task 1: Group words into phrase-level ASS dialogue events

**Files:**
- Modify: `src/movie_shorts/services/subtitles.py`
- Modify: `tests/unit/test_subtitles.py`

**Interfaces:**
- Produces `group_words(words: tuple[WordTiming, ...]) -> list[tuple[WordTiming, ...]]`.
- `build_ass(words, video_start)` emits one dialogue line per returned group.

- [ ] **Step 1: Write failing tests**

```python
def test_groups_close_words_into_one_dialogue_line() -> None:
    words = (WordTiming(10, 10.2, "Я"), WordTiming(10.25, 10.5, "не"), WordTiming(10.55, 10.9, "хочу"))
    ass = build_ass(words, video_start=10)
    assert ass.count("Dialogue:") == 1
    assert "Я" in ass and "не" in ass and "хочу" in ass

def test_splits_phrase_after_long_pause() -> None:
    groups = group_words((WordTiming(0, 0.2, "Да"), WordTiming(1, 1.2, "нет")))
    assert [len(group) for group in groups] == [1, 1]
```

- [ ] **Step 2: Verify failing tests**

Run: `.venv/bin/python -m pytest tests/unit/test_subtitles.py -v`  
Expected: FAIL because grouping does not exist and current ASS has one dialogue line per word.

- [ ] **Step 3: Implement grouping and phrase karaoke rendering**

Create `group_words` that starts a new group before a fifth word, before a word after a 0,45-second pause, or before a word that would make the group last more than 2,5 seconds. In `build_ass`, create one line per group, from the first word start through the last word end. Prepend each word with a `\\k` duration tag and apply the existing yellow colour tag to the word being timed.

- [ ] **Step 4: Verify tests and regression suite**

Run: `.venv/bin/python -m pytest tests/unit/test_subtitles.py -v`  
Expected: PASS.

Run: `.venv/bin/python -m pytest -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/movie_shorts/services/subtitles.py tests/unit/test_subtitles.py
git commit -m "feat: group karaoke subtitle words"
```
