from movie_shorts.storage import RunStorage


def test_storage_writes_and_reads_a_completed_stage(tmp_path) -> None:
    storage = RunStorage.create(tmp_path, {"language": "ru"})

    storage.save_stage("scenes", [{"id": 1, "start": 0.0, "end": 3.5}])

    assert storage.load_stage("scenes") == [{"id": 1, "start": 0.0, "end": 3.5}]
    assert storage.manifest()["stages"]["scenes"]["status"] == "completed"


def test_storage_does_not_read_incomplete_stage(tmp_path) -> None:
    storage = RunStorage.create(tmp_path, {})

    assert storage.load_stage("scenes") is None
