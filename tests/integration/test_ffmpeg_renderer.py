import shutil
import subprocess
from pathlib import Path

import pytest

from movie_shorts.config import BackgroundMusicConfig
from movie_shorts.models import Candidate
from movie_shorts.services.music import MusicSelection
from movie_shorts.services.renderer import render_short


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg не установлен")
def test_renderer_creates_vertical_mp4_with_audio(tmp_path, sample_video) -> None:
    output = render_short(sample_video, Candidate(1, 0, 2, (1,), ""), None, tmp_path / "out.mp4")

    assert output.exists()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg не установлен")
def test_renderer_mixes_background_music_with_source_audio(tmp_path, sample_video) -> None:
    music_path = tmp_path / "music.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=1",
            str(music_path),
        ],
        check=True,
        capture_output=True,
    )
    music_config = BackgroundMusicConfig(music_path, music_path)
    selection = MusicSelection("epic", music_path, 75)
    output = render_short(
        sample_video,
        Candidate(1, 0, 2, (1,), ""),
        None,
        tmp_path / "out.mp4",
        music=selection,
        music_config=music_config,
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert probe.stdout.strip() == "audio"
