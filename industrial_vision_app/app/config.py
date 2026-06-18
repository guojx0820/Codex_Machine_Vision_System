from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


@dataclass
class CameraConfig:
    type: str = "simulator"
    simulator_image_dir: str = "samples"
    width: int = 1280
    height: int = 720
    fps: int = 15


@dataclass
class ModelConfig:
    backend: str = "dummy"
    weights: str = "yolov8n.pt"
    confidence: float = 0.35
    device: str = "cpu"


@dataclass
class PlcConfig:
    enabled: bool = False
    host: str = "192.168.1.10"
    port: int = 502
    ok_coil: int = 0
    ng_coil: int = 1


@dataclass
class DatabaseConfig:
    url: str = "sqlite:///records.db"


@dataclass
class RuntimeConfig:
    save_ng_images: bool = True
    ng_dir: str = "ng_images"


@dataclass
class AppConfig:
    camera: CameraConfig
    model: ModelConfig
    plc: PlcConfig
    database: DatabaseConfig
    runtime: RuntimeConfig


def _load_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yml", ".yaml"} and yaml:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def load_config(path: str | Path) -> AppConfig:
    data = _load_mapping(Path(path))
    return AppConfig(
        camera=CameraConfig(**data.get("camera", {})),
        model=ModelConfig(**data.get("model", {})),
        plc=PlcConfig(**data.get("plc", {})),
        database=DatabaseConfig(**data.get("database", {})),
        runtime=RuntimeConfig(**data.get("runtime", {})),
    )
