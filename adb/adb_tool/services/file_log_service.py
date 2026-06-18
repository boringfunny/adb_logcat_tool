"""Background loader for large log files."""
from __future__ import annotations

import os
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal

from adb_tool.models.log_entry import LogEntry
from adb_tool.utils.logger import get_logger

logger = get_logger()


class FileLogLoader(QThread):
    batch_loaded = pyqtSignal(list)
    progress_changed = pyqtSignal(int)
    finished_loading = pyqtSignal(int, bool)
    error = pyqtSignal(str)

    def __init__(self, filepath: str, max_bytes: int = 16 * 1024 * 1024, batch_size: int = 1000):
        super().__init__()
        self.filepath = filepath
        self.max_bytes = max_bytes
        self.batch_size = batch_size
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            file_size = os.path.getsize(self.filepath)
            truncated = file_size > self.max_bytes
            start = max(0, file_size - self.max_bytes)
            total_read = 0
            total_lines = 0
            batch: List[LogEntry] = []

            with open(self.filepath, "rb") as source:
                source.seek(start)
                if start > 0:
                    source.readline()

                while self._running:
                    raw = source.readline()
                    if not raw:
                        break
                    total_read += len(raw)
                    line = raw.decode("utf-8", errors="ignore").rstrip("\r\n")
                    if not line:
                        continue
                    entry = LogEntry.parse(line)
                    if entry:
                        batch.append(entry)
                        total_lines += 1
                    if len(batch) >= self.batch_size:
                        self.batch_loaded.emit(batch)
                        batch = []
                        self.progress_changed.emit(self._progress(total_read, file_size, start))

            if batch and self._running:
                self.batch_loaded.emit(batch)
            self.progress_changed.emit(100)
            self.finished_loading.emit(total_lines, truncated)
            logger.info(f"日志文件加载完成: {self.filepath}, lines={total_lines}, truncated={truncated}")
        except Exception as exc:
            logger.error(f"日志文件加载失败: {exc}")
            self.error.emit(str(exc))

    def _progress(self, total_read: int, file_size: int, start: int) -> int:
        remaining = max(1, file_size - start)
        return min(99, int(total_read / remaining * 100))
