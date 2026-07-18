import subprocess

from movie_shorts.services.media import probe_media, resolve_device


def test_probe_reads_duration_and_streams(monkeypatch, tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()

    def fake_ffprobe(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"format": {"duration": "95.4"}, "streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}',
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_ffprobe)

    info = probe_media(source)

    assert info.duration == 95.4
    assert info.has_video is True
    assert info.has_audio is True


def test_auto_falls_back_to_cpu_when_cuda_is_not_available(monkeypatch) -> None:
    monkeypatch.setattr("movie_shorts.services.media.cuda_available", lambda: False)

    assert resolve_device("auto") == "cpu"
