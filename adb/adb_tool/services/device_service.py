"""设备管理服务"""
from typing import List, Optional
from adb_tool.models.device import AdbDevice, DeviceStatus
from adb_tool.services.adb_service import AdbService
from adb_tool.utils.logger import get_logger

logger = get_logger()


class DeviceService:
    def __init__(self, adb_service: AdbService):
        self.adb_service = adb_service
        self._devices: List[AdbDevice] = []
    
    def get_devices(self) -> List[AdbDevice]:
        code, stdout, stderr = self.adb_service.get_devices()
        
        if code != 0:
            logger.error(f"获取设备列表失败: {stderr}")
            return []
        
        self._devices = []
        lines = stdout.strip().split('\n')
        
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            device = AdbDevice.parse_from_adb_output(line)
            if device:
                self._devices.append(device)
        
        logger.info(f"发现 {len(self._devices)} 个设备")
        return self._devices
    
    def get_device_by_serial(self, serial: str) -> Optional[AdbDevice]:
        for device in self._devices:
            if device.serial == serial:
                return device
        return None
    
    def connect(self, address: str) -> tuple[bool, str]:
        code, stdout, stderr = self.adb_service.connect(address)
        
        if code != 0:
            return False, stderr or "连接失败"
        
        if "connected" in stdout.lower():
            logger.info(f"成功连接到 {address}")
            return True, f"已连接到 {address}"
        elif "already connected" in stdout.lower():
            return True, f"已连接到 {address}"
        else:
            return False, stdout or "连接失败"
    
    def disconnect(self, address: Optional[str] = None) -> tuple[bool, str]:
        code, stdout, stderr = self.adb_service.disconnect(address)
        
        if code != 0:
            return False, stderr or "断开连接失败"
        
        target = address or "所有设备"
        logger.info(f"已断开 {target}")
        return True, f"已断开 {target}"
    
    def restart_adb_server(self) -> tuple[bool, str]:
        code, stdout, stderr = self.adb_service.restart_server()
        
        if code != 0:
            return False, stderr or "重启 ADB 服务失败"
        
        logger.info("ADB 服务已重启")
        return True, "ADB 服务已重启"
    
    def get_online_devices(self) -> List[AdbDevice]:
        return [d for d in self._devices if d.is_online]
    
    def has_devices(self) -> bool:
        return len(self.get_online_devices()) > 0
