import json
from pathlib import Path
from typing import Any


class RunStorage:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self._manifest_path = output_dir / "manifest.json"

    @classmethod
    def create(cls, output_dir: Path, parameters: dict[str, Any]) -> "RunStorage":
        output_dir.mkdir(parents=True, exist_ok=True)
        for directory in ("logs", "shorts", "subtitles"):
            (output_dir / directory).mkdir(exist_ok=True)

        storage = cls(output_dir)
        if not storage._manifest_path.exists():
            storage._write_json(storage._manifest_path, {"parameters": parameters, "stages": {}})
        return storage

    def manifest(self) -> dict[str, Any]:
        return self._read_json(self._manifest_path)

    def mark_stage(self, name: str, status: str, message: str | None = None) -> None:
        manifest = self.manifest()
        stage: dict[str, Any] = {"status": status}
        if message is not None:
            stage["message"] = message
        manifest.setdefault("stages", {})[name] = stage
        self._write_json(self._manifest_path, manifest)

    def save_stage(self, name: str, payload: Any) -> None:
        self._write_json(self.output_dir / f"{name}.json", payload)
        self.mark_stage(name, "completed")

    def load_stage(self, name: str) -> Any | None:
        if self.manifest().get("stages", {}).get(name, {}).get("status") != "completed":
            return None

        path = self.output_dir / f"{name}.json"
        try:
            return self._read_json(path)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def log_debug(self, message: str) -> None:
        with (self.output_dir / "logs" / "debug.log").open("a", encoding="utf-8") as file:
            file.write(f"{message}\n")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        temporary_path.replace(path)
