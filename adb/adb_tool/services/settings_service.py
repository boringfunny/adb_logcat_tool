"""设置服务"""
import json
import os
from typing import Optional
from ..models.settings import AppSettings
from ..utils.logger import get_logger

logger = get_logger()


class SettingsService:
    def __init__(self):
        self._settings = AppSettings()
        self._config_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'AdbTool')
        self._config_file = os.path.join(self._config_dir, 'config.json')
        self._ensure_config_dir()
        self.load()
    
    def _ensure_config_dir(self):
        os.makedirs(self._config_dir, exist_ok=True)
    
    @property
    def settings(self) -> AppSettings:
        return self._settings
    
    def load(self) -> bool:
        if not os.path.exists(self._config_file):
            logger.info("配置文件不存在，使用默认设置")
            return True
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._settings = AppSettings.from_dict(data)
            logger.info("配置已加载")
            return True
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False
    
    def save(self) -> bool:
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info("配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get(self, key: str, default=None):
        return getattr(self._settings, key, default)
    
    def set(self, key: str, value):
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
            return True
        return False
