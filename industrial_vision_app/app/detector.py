from __future__ import annotations

from dataclasses import dataclass
import time

import cv2
import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    xyxy: tuple[int, int, int, int]


@dataclass
class InspectionResult:
    is_ok: bool
    detections: list[Detection]
    latency_ms: float
    annotated: np.ndarray


class DummyDefectDetector:
    """Red-area detector for end-to-end software validation before model training."""

    def __init__(self, confidence: float = 0.35):
        self.confidence = confidence

    def predict(self, frame: np.ndarray) -> InspectionResult:
        started = time.perf_counter()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, (0, 80, 80), (12, 255, 255))
        mask2 = cv2.inRange(hsv, (168, 80, 80), (180, 255, 255))
        mask = cv2.morphologyEx(mask1 | mask2, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        annotated = frame.copy()
        detections: list[Detection] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            det = Detection("defect", min(0.99, area / 5000), (x, y, x + w, y + h))
            detections.append(det)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(annotated, f"{det.label} {det.confidence:.2f}", (x, max(30, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        latency = (time.perf_counter() - started) * 1000
        return InspectionResult(is_ok=not detections, detections=detections, latency_ms=latency, annotated=annotated)


class UltralyticsDetector:
    def __init__(self, weights: str, confidence: float = 0.35, device: str = "cpu"):
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.confidence = confidence
        self.device = device

    def predict(self, frame: np.ndarray) -> InspectionResult:
        started = time.perf_counter()
        results = self.model.predict(frame, conf=self.confidence, device=self.device, verbose=False)
        annotated = results[0].plot()
        detections: list[Detection] = []
        names = results[0].names
        for box in results[0].boxes:
            xyxy = tuple(int(v) for v in box.xyxy[0].tolist())
            cls_id = int(box.cls[0].item())
            detections.append(Detection(names.get(cls_id, str(cls_id)), float(box.conf[0].item()), xyxy))
        latency = (time.perf_counter() - started) * 1000
        return InspectionResult(is_ok=not detections, detections=detections, latency_ms=latency, annotated=annotated)


def build_detector(cfg):
    if cfg.backend == "dummy":
        return DummyDefectDetector(cfg.confidence)
    if cfg.backend == "ultralytics":
        return UltralyticsDetector(cfg.weights, cfg.confidence, cfg.device)
    raise ValueError(f"Unknown model backend: {cfg.backend}")
