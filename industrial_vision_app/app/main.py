from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QTextEdit

from app.camera import build_camera
from app.config import load_config
from app.detector import build_detector
from app.plc import PlcClient
from app.storage import RecordStore


class InspectionWorker(QThread):
    frame_ready = Signal(object, object)
    log_ready = Signal(str)

    def __init__(self, config_path: str):
        super().__init__()
        self.cfg = load_config(config_path)
        self.running = False

    def run(self) -> None:
        camera = build_camera(self.cfg.camera)
        detector = build_detector(self.cfg.model)
        plc = PlcClient(**self.cfg.plc.__dict__)
        store = RecordStore(self.cfg.database.url)
        ng_dir = Path(self.cfg.runtime.ng_dir)
        ng_dir.mkdir(exist_ok=True)
        try:
            camera.open()
            plc.connect()
            self.running = True
            self.log_ready.emit("产线检测已启动")
            while self.running:
                frame = camera.read()
                result = detector.predict(frame)
                image_path = ""
                if (not result.is_ok) and self.cfg.runtime.save_ng_images:
                    image_path = str(ng_dir / f"NG_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg")
                    cv2.imwrite(image_path, result.annotated)
                store.insert(result.is_ok, len(result.detections), result.latency_ms, image_path)
                plc.publish_result(result.is_ok)
                self.frame_ready.emit(result.annotated, result)
        except Exception as exc:  # keep UI alive and show operational error
            self.log_ready.emit(f"ERROR: {exc}")
        finally:
            camera.close()
            plc.close()
            store.close()
            self.log_ready.emit("产线检测已停止")

    def stop(self) -> None:
        self.running = False
        self.wait(3000)


class MainWindow(QMainWindow):
    def __init__(self, config_path: str):
        super().__init__()
        self.setWindowTitle("工业机器视觉缺陷检测工作站")
        self.resize(1280, 860)
        self.worker = InspectionWorker(config_path)
        self.worker.frame_ready.connect(self.on_frame)
        self.worker.log_ready.connect(self.on_log)

        self.image_label = QLabel("点击启动开始检测")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(960, 540)
        self.status_label = QLabel("状态：待机")
        self.log_box = QTextEdit(readOnly=True)
        self.start_btn = QPushButton("启动检测")
        self.stop_btn = QPushButton("停止检测")
        self.start_btn.clicked.connect(self.worker.start)
        self.stop_btn.clicked.connect(self.worker.stop)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.stop_btn)
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        layout.addWidget(self.log_box)
        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

    def on_frame(self, frame, result) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(image).scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        color = "green" if result.is_ok else "red"
        text = f"状态：{'OK 合格' if result.is_ok else 'NG 缺陷'} | 缺陷数：{len(result.detections)} | 延迟：{result.latency_ms:.1f} ms"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")

    def on_log(self, message: str) -> None:
        self.log_box.append(f"{datetime.now().strftime('%H:%M:%S')} {message}")

    def closeEvent(self, event) -> None:
        self.worker.stop()
        event.accept()


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    app = QApplication(sys.argv)
    window = MainWindow(config_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
