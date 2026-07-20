from movie_shorts.models import WordTiming
from movie_shorts.services.subtitles import build_ass, group_words


def test_ass_contains_russian_style_and_relative_timestamps() -> None:
    ass = build_ass((WordTiming(10.0, 10.5, "Привет"),), video_start=10.0)

    assert "PlayResY: 1920" in ass
    assert "0:00:00.00" in ass
    assert "Привет" in ass


def test_groups_close_words_into_one_dialogue_line() -> None:
    words = (
        WordTiming(10.0, 10.2, "Я"),
        WordTiming(10.25, 10.5, "не"),
        WordTiming(10.55, 10.9, "хочу"),
    )

    ass = build_ass(words, video_start=10.0)

    assert ass.count("Dialogue:") == 1
    assert "Я" in ass and "не" in ass and "хочу" in ass


def test_splits_phrase_after_long_pause_and_three_words() -> None:
    words = (
        WordTiming(0.0, 0.1, "раз"), WordTiming(0.12, 0.2, "два"),
        WordTiming(0.22, 0.3, "три"), WordTiming(0.32, 0.4, "четыре"),
        WordTiming(0.42, 0.5, "пять"), WordTiming(1.1, 1.2, "шесть"),
    )

    groups = group_words(words)

    assert [len(group) for group in groups] == [3, 2, 1]


def test_karaoke_keeps_pause_before_the_next_word() -> None:
    ass = build_ass((WordTiming(0, 0.2, "раз"), WordTiming(0.5, 0.7, "два")), video_start=0)

    assert "Style: Default,Arial,92" in ass
    assert "{\\k20}раз {\\k30} {\\k20}два" in ass
