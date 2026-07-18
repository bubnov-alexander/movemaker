from pathlib import Path

from movie_shorts.models import Candidate
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
