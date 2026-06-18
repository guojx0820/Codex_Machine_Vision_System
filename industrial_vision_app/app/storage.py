from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3


class RecordStore:
    def __init__(self, sqlite_url: str):
        self.path = sqlite_url.replace("sqlite:///", "") if sqlite_url.startswith("sqlite:///") else sqlite_url
        Path(self.path).parent.mkdir(parents=True, exist_ok=True) if Path(self.path).parent != Path('.') else None
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS inspections (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, result TEXT, defect_count INTEGER, latency_ms REAL, image_path TEXT)"
        )
        self.conn.commit()

    def insert(self, is_ok: bool, defect_count: int, latency_ms: float, image_path: str = "") -> None:
        self.conn.execute(
            "INSERT INTO inspections(created_at, result, defect_count, latency_ms, image_path) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), "OK" if is_ok else "NG", defect_count, latency_ms, image_path),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
