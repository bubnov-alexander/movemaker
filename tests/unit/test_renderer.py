from pathlib import Path

from movie_shorts.config import BackgroundMusicConfig
from movie_shorts.models import Candidate
from movie_shorts.services.music import MusicSelection
from movie_shorts.services.renderer import render_command


def test_render_command_creates_vertical_video_with_ass_subtitles() -> None:
    command = render_command(
        Path("film.mp4"),
        Candidate(1, 10, 30, (1,), ""),
        Path("subtitles/short-01.ass"),
        Path("shorts/short-01.tmp.mp4"),
    )

    assert command[0] == "ffmpeg"
    assert "-ss" in command
    assert "1080:1920" in " ".join(command)
    assert "ass=subtitles/short-01.ass" in " ".join(command)


def test_render_command_ducks_looped_background_music() -> None:
    music_config = BackgroundMusicConfig(Path("music/yaya.mp3"), Path("music/altyn.mp3"))
    selection = MusicSelection("epic", Path("music/yaya.mp3"), 75)

    command = render_command(
        Path("film.mp4"),
        Candidate(7, 10, 30, (), ""),
        None,
        Path("out.mp4"),
        selection,
        music_config,
    )

    rendered = " ".join(command)
    assert command.count("-i") == 2
    assert "-stream_loop -1" in rendered
    assert "atrim=duration=20" in rendered
    assert "sidechaincompress=threshold=0.08:ratio=4" in rendered
    assert "[mixed]" in rendered


def test_render_command_places_looped_layout_video_in_top_third() -> None:
    command = render_command(
        Path("film.mp4"),
        Candidate(1, 10, 30, (), ""),
        None,
        Path("out.mp4"),
        layout_background_path=Path("backgrounds/background.mp4"),
    )

    rendered = " ".join(command)

    assert command.count("-i") == 2
    assert "-stream_loop -1 -i backgrounds/background.mp4" in rendered
    assert "crop=1080:480" in rendered
    assert "crop=1080:960" in rendered
    assert "overlay=0:0" in rendered
    assert "overlay=0:480" in rendered
