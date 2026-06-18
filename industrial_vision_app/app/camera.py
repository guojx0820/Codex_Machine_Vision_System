from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


class Camera(Protocol):
    def open(self) -> None: ...
    def read(self) -> np.ndarray: ...
    def close(self) -> None: ...


class SimulatorCamera:
    """Camera replacement for development without industrial hardware."""

    def __init__(self, image_dir: str, width: int = 1280, height: int = 720, fps: int = 15):
        self.image_dir = Path(image_dir)
        self.width = width
        self.height = height
        self.delay = 1.0 / max(fps, 1)
        self._images: list[Path] = []
        self._idx = 0

    def open(self) -> None:
        if self.image_dir.exists():
            self._images = sorted(
                p for p in self.image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
            )

    def read(self) -> np.ndarray:
        time.sleep(self.delay)
        if self._images:
            img = cv2.imread(str(self._images[self._idx % len(self._images)]))
            self._idx += 1
            if img is not None:
                return cv2.resize(img, (self.width, self.height))
        return self._synthetic_frame()

    def close(self) -> None:
        pass

    def _synthetic_frame(self) -> np.ndarray:
        frame = np.full((self.height, self.width, 3), 38, dtype=np.uint8)
        cv2.rectangle(frame, (220, 160), (980, 560), (95, 95, 95), -1)
        cv2.putText(frame, "SIMULATED PART", (360, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (220, 220, 220), 3)
        x = 330 + (self._idx * 17) % 520
        y = 250 + (self._idx * 11) % 180
        cv2.circle(frame, (x, y), 32, (0, 0, 255), -1)
        cv2.putText(frame, "defect", (x - 45, y - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        self._idx += 1
        return frame


class OpenCVCamera:
    def __init__(self, index: int = 0):
        self.index = index
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.index}")

    def read(self) -> np.ndarray:
        if self.cap is None:
            raise RuntimeError("Camera not opened")
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Camera frame grab failed")
        return frame

    def close(self) -> None:
        if self.cap:
            self.cap.release()


def build_camera(cfg) -> Camera:
    if cfg.type == "simulator":
        return SimulatorCamera(cfg.simulator_image_dir, cfg.width, cfg.height, cfg.fps)
    if cfg.type == "opencv":
        return OpenCVCamera(0)
    raise NotImplementedError(f"请在 app/camera.py 中接入 {cfg.type} 官方 SDK")
