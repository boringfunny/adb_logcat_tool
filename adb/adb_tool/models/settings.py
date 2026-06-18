"""应用设置模型"""
from dataclasses import dataclass, field
from typing import Optional, List
import json
import os


@dataclass
class AppSettings:
    adb_path: Optional[str] = None
    auto_refresh_devices: bool = True
    device_refresh_interval: int = 5
    log_buffer_size: int = 100000
    auto_scroll_log: bool = True
    recent_keywords: List[str] = field(default_factory=list)
    recent_tags: List[str] = field(default_factory=list)
    window_geometry: Optional[bytes] = None
    window_state: Optional[bytes] = None
    
    def to_dict(self) -> dict:
        return {
            "adb_path": self.adb_path,
            "auto_refresh_devices": self.auto_refresh_devices,
            "device_refresh_interval": self.device_refresh_interval,
            "log_buffer_size": self.log_buffer_size,
            "auto_scroll_log": self.auto_scroll_log,
            "recent_keywords": self.recent_keywords,
            "recent_tags": self.recent_tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppSettings':
        return cls(
            adb_path=data.get("adb_path"),
            auto_refresh_devices=data.get("auto_refresh_devices", True),
            device_refresh_interval=data.get("device_refresh_interval", 5),
            log_buffer_size=data.get("log_buffer_size", 100000),
            auto_scroll_log=data.get("auto_scroll_log", True),
            recent_keywords=data.get("recent_keywords", []),
            recent_tags=data.get("recent_tags", [])
        )
    
    def add_recent_keyword(self, keyword: str):
        if keyword in self.recent_keywords:
            self.recent_keywords.remove(keyword)
        self.recent_keywords.insert(0, keyword)
        self.recent_keywords = self.recent_keywords[:20]
    
    def add_recent_tag(self, tag: str):
        if tag in self.recent_tags:
            self.recent_tags.remove(tag)
        self.recent_tags.insert(0, tag)
        self.recent_tags = self.recent_tags[:20]
