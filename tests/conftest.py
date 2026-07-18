import shutil
import subprocess

import pytest


@pytest.fixture()
def sample_video(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg не установлен")
    path = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest", str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path
