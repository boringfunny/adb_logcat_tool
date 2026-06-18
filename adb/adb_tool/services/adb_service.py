"""ADB 核心服务"""
import os
from typing import Optional, Tuple
from adb_tool.utils.process_utils import execute_command, execute_adb
from adb_tool.utils.env_utils import find_in_path
from adb_tool.utils.logger import get_logger

logger = get_logger()


class AdbService:
    PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    
    def __init__(self, adb_path: Optional[str] = None):
        self._adb_path = adb_path
        self._version: Optional[str] = None
    
    @property
    def adb_path(self) -> str:
        if self._adb_path:
            return self._adb_path
        
        path = find_in_path("adb")
        if path:
            adb_exe = os.path.join(path, "adb.exe")
            if os.path.isfile(adb_exe):
                self._adb_path = adb_exe
                return adb_exe
        
        return "adb"
    
    @adb_path.setter
    def adb_path(self, value: str):
        self._adb_path = value
        self._version = None
    
    def is_available(self) -> bool:
        code, _, _ = self.execute("version")
        return code == 0
    
    def get_version(self) -> Optional[str]:
        if self._version:
            return self._version
        
        code, stdout, _ = self.execute("version")
        if code == 0:
            for line in stdout.split('\n'):
                if "Android Debug Bridge" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        self._version = parts[4]
                        return self._version
        return None
    
    def execute(
        self,
        args: str,
        timeout: int = 30,
        device_id: Optional[str] = None
    ) -> Tuple[int, str, str]:
        cmd = self.adb_path
        if device_id:
            cmd += f" -s {device_id}"
        cmd += f" {args}"
        
        logger.debug(f"执行 ADB 命令: {cmd}")
        return execute_command(cmd, timeout)
    
    def start_server(self) -> Tuple[int, str, str]:
        logger.info("启动 ADB 服务器")
        return self.execute("start-server")
    
    def kill_server(self) -> Tuple[int, str, str]:
        logger.info("停止 ADB 服务器")
        return self.execute("kill-server")
    
    def restart_server(self) -> Tuple[int, str, str]:
        self.kill_server()
        return self.start_server()
    
    def get_devices(self) -> Tuple[int, str, str]:
        return self.execute("devices -l")
    
    def connect(self, address: str) -> Tuple[int, str, str]:
        logger.info(f"连接设备: {address}")
        return self.execute(f"connect {address}")
    
    def disconnect(self, address: Optional[str] = None) -> Tuple[int, str, str]:
        if address:
            logger.info(f"断开设备: {address}")
            return self.execute(f"disconnect {address}")
        else:
            logger.info("断开所有设备")
            return self.execute("disconnect")
    
    def shell(
        self,
        command: str,
        device_id: Optional[str] = None
    ) -> Tuple[int, str, str]:
        return self.execute(f'shell "{command}"', device_id=device_id)
    
    def get_pid(self, package_name: str, device_id: Optional[str] = None) -> Optional[int]:
        code, stdout, _ = self.shell(f"pidof {package_name}", device_id)
        if code == 0 and stdout.strip():
            try:
                return int(stdout.strip().split()[0])
            except (ValueError, IndexError):
                return None
        return None
