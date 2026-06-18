"""ADB 安装服务"""
import os
import zipfile
import requests
from typing import Optional, Callable
from adb_tool.utils.env_utils import add_to_user_path, find_in_path, refresh_environment
from adb_tool.utils.logger import get_logger
from adb_tool.services.adb_service import AdbService

logger = get_logger()

PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"


class AdbInstaller:
    def __init__(self, adb_service: AdbService):
        self.adb_service = adb_service
        self.install_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'AdbTool')
    
    def is_installed(self) -> bool:
        if self.adb_service.is_available():
            return True
        
        local_path = os.path.join(self.install_dir, 'platform-tools', 'adb.exe')
        if os.path.isfile(local_path):
            self.adb_service.adb_path = local_path
            return self.adb_service.is_available()
        
        return False
    
    def is_locally_installed(self) -> bool:
        local_path = os.path.join(self.install_dir, 'platform-tools', 'adb.exe')
        return os.path.isfile(local_path)
    
    def get_install_path(self) -> Optional[str]:
        if self.is_installed():
            return os.path.dirname(self.adb_service.adb_path)
        return None
    
    def download_platform_tools(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        os.makedirs(self.install_dir, exist_ok=True)
        zip_path = os.path.join(self.install_dir, "platform-tools.zip")
        
        logger.info(f"开始下载 platform-tools: {PLATFORM_TOOLS_URL}")
        
        response = requests.get(PLATFORM_TOOLS_URL, stream=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback(downloaded, total_size)
        
        logger.info("下载完成，开始解压")
        return zip_path
    
    def extract_platform_tools(self, zip_path: str) -> str:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(self.install_dir)
        
        os.remove(zip_path)
        
        platform_tools_dir = os.path.join(self.install_dir, "platform-tools")
        logger.info(f"解压完成: {platform_tools_dir}")
        return platform_tools_dir
    
    def configure_environment(self, path: str) -> bool:
        logger.info(f"配置环境变量: {path}")
        if add_to_user_path(path):
            refresh_environment()
            return True
        return False
    
    def install(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        force: bool = False
    ) -> tuple[bool, str]:
        try:
            if progress_callback:
                progress_callback("检查现有安装...", 0)
            
            if not force and self.is_locally_installed():
                local_path = os.path.join(self.install_dir, 'platform-tools', 'adb.exe')
                self.adb_service.adb_path = local_path
                if progress_callback:
                    progress_callback("安装完成", 100)
                version = self.adb_service.get_version()
                return True, f"ADB 已安装 (v{version})"
            
            if progress_callback:
                progress_callback("下载 platform-tools...", 10)
            
            def download_progress(downloaded: int, total: int):
                if progress_callback and total_size_ref[0] > 0:
                    percent = int(10 + (downloaded / total_size_ref[0]) * 60)
                    progress_callback(f"下载中... {downloaded // 1024}KB / {total_size_ref[0] // 1024}KB", percent)
            
            total_size_ref = [0]
            
            os.makedirs(self.install_dir, exist_ok=True)
            zip_path = os.path.join(self.install_dir, "platform-tools.zip")
            
            logger.info(f"开始下载 platform-tools: {PLATFORM_TOOLS_URL}")
            
            response = requests.get(PLATFORM_TOOLS_URL, stream=True, timeout=60)
            total_size_ref[0] = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size_ref[0] > 0:
                        percent = int(10 + (downloaded / total_size_ref[0]) * 60)
                        progress_callback(f"下载中... {downloaded // 1024}KB / {total_size_ref[0] // 1024}KB", percent)
            
            logger.info("下载完成，开始解压")
            
            if progress_callback:
                progress_callback("解压文件...", 70)
            
            platform_tools_dir = self.extract_platform_tools(zip_path)
            
            if progress_callback:
                progress_callback("配置环境变量...", 80)
            
            adb_exe = os.path.join(platform_tools_dir, "adb.exe")
            self.adb_service.adb_path = adb_exe
            
            if not self.configure_environment(platform_tools_dir):
                logger.warning("配置环境变量失败，但 ADB 可在程序内使用")
            
            if progress_callback:
                progress_callback("验证安装...", 90)
            
            if not self.adb_service.is_available():
                return False, "安装验证失败，请检查 adb.exe 是否存在"
            
            if progress_callback:
                progress_callback("安装完成", 100)
            
            version = self.adb_service.get_version()
            return True, f"安装成功！ADB 版本: {version}"
            
        except requests.RequestException as e:
            logger.error(f"下载失败: {e}")
            return False, f"下载失败: {str(e)}\n请检查网络连接"
        except zipfile.BadZipFile as e:
            logger.error(f"解压失败: {e}")
            return False, f"解压失败: {str(e)}"
        except Exception as e:
            logger.error(f"安装失败: {e}")
            return False, f"安装失败: {str(e)}"
    
    def uninstall(self) -> tuple[bool, str]:
        try:
            platform_tools_dir = os.path.join(self.install_dir, "platform-tools")
            if os.path.exists(platform_tools_dir):
                import shutil
                shutil.rmtree(platform_tools_dir)
                logger.info(f"已删除: {platform_tools_dir}")
            
            return True, "卸载成功"
        except Exception as e:
            logger.error(f"卸载失败: {e}")
            return False, f"卸载失败: {str(e)}"
