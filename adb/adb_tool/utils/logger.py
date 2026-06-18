"""日志记录器"""
import logging
import os
from datetime import datetime
from typing import Optional


_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


def setup_logger(
    name: str = "AdbTool",
    log_dir: Optional[str] = None,
    level: int = logging.DEBUG
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_dir is None:
        log_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'AdbTool', 'logs')
    
    log_file = os.path.join(log_dir, f"adb_tool_{datetime.now().strftime('%Y%m%d')}.log")
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
    except OSError:
        fallback_dir = os.path.join(os.getcwd(), ".adb_tool", "logs")
        os.makedirs(fallback_dir, exist_ok=True)
        fallback_file = os.path.join(fallback_dir, f"adb_tool_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(fallback_file, encoding='utf-8')

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_info(message: str):
    get_logger().info(message)


def log_error(message: str):
    get_logger().error(message)


def log_debug(message: str):
    get_logger().debug(message)


def log_warning(message: str):
    get_logger().warning(message)
