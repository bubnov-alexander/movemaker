import shutil

import pytest

from movie_shorts.models import Candidate
from movie_shorts.services.renderer import render_short


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg не установлен")
def test_renderer_creates_vertical_mp4_with_audio(tmp_path, sample_video) -> None:
    output = render_short(sample_video, Candidate(1, 0, 2, (1,), ""), None, tmp_path / "out.mp4")

    assert output.exists()
