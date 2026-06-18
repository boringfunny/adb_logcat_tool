"""设备数据模型"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeviceStatus(Enum):
    ONLINE = "device"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


@dataclass
class AdbDevice:
    serial: str
    status: DeviceStatus
    model: Optional[str] = None
    product: Optional[str] = None
    device: Optional[str] = None
    transport_id: Optional[int] = None
    
    @property
    def is_online(self) -> bool:
        return self.status == DeviceStatus.ONLINE
    
    @property
    def display_name(self) -> str:
        parts = [self.serial]
        if self.model:
            parts.append(f"({self.model})")
        parts.append(f"[{self.status.value}]")
        return " ".join(parts)
    
    @classmethod
    def parse_from_adb_output(cls, line: str) -> Optional['AdbDevice']:
        parts = line.split()
        if len(parts) < 2:
            return None
        
        serial = parts[0]
        status_str = parts[1]
        
        try:
            status = DeviceStatus(status_str)
        except ValueError:
            status = DeviceStatus.UNKNOWN
        
        model = None
        product = None
        device = None
        transport_id = None
        
        for part in parts[2:]:
            if part.startswith("model:"):
                model = part[6:]
            elif part.startswith("product:"):
                product = part[8:]
            elif part.startswith("device:"):
                device = part[7:]
            elif part.startswith("transport_id:"):
                transport_id = int(part[13:])
        
        return cls(
            serial=serial,
            status=status,
            model=model,
            product=product,
            device=device,
            transport_id=transport_id
        )
