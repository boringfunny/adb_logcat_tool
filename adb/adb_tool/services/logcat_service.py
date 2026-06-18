"""日志服务"""
import subprocess
from typing import Optional, List
from PyQt5.QtCore import QThread, pyqtSignal, QObject, Qt, QTimer
from adb_tool.models.log_entry import LogEntry, LogLevel
from adb_tool.services.adb_service import AdbService
from adb_tool.utils.logger import get_logger

logger = get_logger()


class LogcatThread(QThread):
    log_batch_received = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        adb_service: AdbService,
        device_id: Optional[str] = None,
        tag: Optional[str] = None,
        level: Optional[LogLevel] = None,
        pid: Optional[int] = None
    ):
        super().__init__()
        self.adb_service = adb_service
        self.device_id = device_id
        self.tag = tag
        self.level = level
        self.pid = pid
        self._running = False
        self._process: Optional[subprocess.Popen] = None
        self._batch_size = 100
        self._batch_timeout = 0.15
    
    def run(self):
        self._running = True
        
        try:
            adb_path = self.adb_service.adb_path
            cmd = [adb_path]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.append("logcat")
            
            if self.pid:
                cmd.append(f"--pid={self.pid}")
            
            if self.tag:
                cmd.extend(["-s", self.tag])
            
            if self.level and not self.tag:
                cmd.append(f"*:{self.level.value}")
            
            logger.info(f"启动 logcat: {' '.join(cmd)}")
            
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            batch: List[LogEntry] = []
            for line in self._process.stdout:
                if not self._running:
                    break
                
                clean_line = line.rstrip('\n\r')
                if not clean_line:
                    continue
                entry = LogEntry.parse(clean_line)
                if entry:
                    batch.append(entry)
                
                if len(batch) >= self._batch_size:
                    self.log_batch_received.emit(batch.copy())
                    batch.clear()
            
            if batch:
                self.log_batch_received.emit(batch)
        
        except Exception as e:
            logger.error(f"logcat 错误: {e}")
            self.error.emit(str(e))
    
    def stop(self):
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        logger.info("logcat 已停止")


class LogcatService(QObject):
    log_batch_received = pyqtSignal(list)
    started = pyqtSignal()
    stopped = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, adb_service: AdbService, parent=None):
        super().__init__(parent)
        self.adb_service = adb_service
        self._thread: Optional[LogcatThread] = None
        self._entries: List[LogEntry] = []
        self._max_entries = 100000
        self._pending_batch: List[LogEntry] = []
        self._batch_timer = QTimer(self)
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._flush_pending_batch)
        self._batch_flush_interval = 100
    
    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()
    
    def start(
        self,
        device_id: Optional[str] = None,
        tag: Optional[str] = None,
        level: Optional[LogLevel] = None,
        pid: Optional[int] = None
    ):
        if self.is_running:
            self.stop()
        
        self._entries = []
        self._thread = LogcatThread(
            self.adb_service,
            device_id=device_id,
            tag=tag,
            level=level,
            pid=pid
        )
        self._thread.log_batch_received.connect(self._on_log_batch_received, Qt.QueuedConnection)
        self._thread.error.connect(self.error, Qt.QueuedConnection)
        self._thread.finished.connect(self._on_finished)
        self._thread.start()
        self.started.emit()
        logger.info("logcat 服务已启动")
    
    def stop(self):
        if self._thread:
            self._thread.stop()
            self._thread = None
        self._batch_timer.stop()
        self._flush_pending_batch()
        self.stopped.emit()
        logger.info("logcat 服务已停止")
    
    def _on_log_batch_received(self, entries: List[LogEntry]):
        self._pending_batch.extend(entries)
        self._entries.extend(entries)
        
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        
        if not self._batch_timer.isActive():
            self._batch_timer.start(self._batch_flush_interval)
    
    def _flush_pending_batch(self):
        if self._pending_batch:
            batch = self._pending_batch.copy()
            self._pending_batch.clear()
            self.log_batch_received.emit(batch)
    
    def _on_finished(self):
        self._thread = None
        self.stopped.emit()
    
    def get_entries(
        self,
        tag: Optional[str] = None,
        level: Optional[LogLevel] = None,
        keyword: Optional[str] = None,
        pid: Optional[int] = None
    ) -> List[LogEntry]:
        result = []
        for entry in self._entries:
            if entry.matches_filter(tag=tag, level=level, keyword=keyword, pid=pid):
                result.append(entry)
        return result
    
    def clear_entries(self):
        self._entries = []
    
    def save_to_file(self, filepath: str) -> bool:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self._entries:
                    f.write(entry.raw_line + '\n')
            logger.info(f"日志已保存到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"保存日志失败: {e}")
            return False
    
    def get_pid_by_package(self, package_name: str, device_id: Optional[str] = None) -> Optional[int]:
        return self.adb_service.get_pid(package_name, device_id)
