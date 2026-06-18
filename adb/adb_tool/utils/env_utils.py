"""环境变量工具"""
import os
import winreg
from typing import Optional


def get_user_path() -> str:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ
        )
        try:
            path, _ = winreg.QueryValueEx(key, "PATH")
            return path if path else ""
        except FileNotFoundError:
            return ""
        finally:
            winreg.CloseKey(key)
    except Exception:
        return ""


def add_to_user_path(path: str) -> bool:
    try:
        path = os.path.abspath(path)
        current_path = get_user_path()
        
        if path.lower() in current_path.lower():
            return True
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_ALL_ACCESS
        )
        try:
            new_path = f"{path};{current_path}" if current_path else path
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def remove_from_user_path(path: str) -> bool:
    try:
        path = os.path.abspath(path).lower()
        current_path = get_user_path()
        
        if path not in current_path.lower():
            return True
        
        paths = current_path.split(';')
        new_paths = [p for p in paths if p.lower() != path and p.strip()]
        new_path = ';'.join(new_paths)
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_ALL_ACCESS
        )
        try:
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def find_in_path(executable: str) -> Optional[str]:
    path_env = os.environ.get("PATH", "")
    paths = path_env.split(os.pathsep)
    
    for path in paths:
        full_path = os.path.join(path, executable)
        if os.name == 'nt':
            full_path += ".exe"
        if os.path.isfile(full_path):
            return os.path.dirname(full_path)
    return None


def refresh_environment():
    import ctypes
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A
    SMTO_ABORTIFHUNG = 0x0002
    result = ctypes.c_long()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_SETTINGCHANGE,
        0,
        "Environment",
        SMTO_ABORTIFHUNG,
        5000,
        ctypes.byref(result)
    )
