# ADB 工具管理器 - 开发计划

## 项目概述
开发一个 Windows 桌面应用程序，提供 ADB 一键安装配置和可视化操作功能。

## 技术选型
- **开发语言**: Python 3.10+
- **UI框架**: PyQt5 (功能强大，界面美观)
- **打包工具**: PyInstaller (打包为独立 exe)
- **核心依赖**: 
  - PyQt5 - GUI 框架
  - requests - HTTP 下载
  - psutil - 进程管理

## 项目结构
```
e:\ai\adb\
├── adb_tool/
│   ├── __init__.py
│   ├── main.py                    # 程序入口
│   ├── main_window.py             # 主窗口 UI
│   ├── models/
│   │   ├── __init__.py
│   │   ├── device.py              # 设备数据模型
│   │   ├── log_entry.py           # 日志条目模型
│   │   └── settings.py            # 应用设置模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── adb_service.py         # ADB 核心服务
│   │   ├── adb_installer.py       # ADB 安装服务
│   │   ├── device_service.py      # 设备管理服务
│   │   ├── logcat_service.py      # 日志服务
│   │   └── settings_service.py    # 设置服务
│   ├── views/
│   │   ├── __init__.py
│   │   ├── device_panel.py        # 设备面板
│   │   ├── log_panel.py           # 日志面板
│   │   └── install_dialog.py      # 安装对话框
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── process_utils.py       # 进程辅助工具
│   │   ├── env_utils.py           # 环境变量工具
│   │   └── logger.py              # 日志记录器
│   └── resources/
│       └── styles.qss             # Qt 样式表
├── requirements.txt               # 依赖列表
├── build.spec                     # PyInstaller 配置
└── README.md                      # 项目说明
```

## 功能模块实现计划

### 模块一：ADB 安装与配置 (adb_installer.py)
1. **环境检测**
   - 检查 PATH 环境变量中是否存在 adb
   - 尝试执行 `adb version` 验证可用性
   - 检查常见安装目录

2. **下载与安装**
   - 使用 requests 下载 platform-tools
   - 下载地址: https://dl.google.com/android/repository/platform-tools-latest-windows.zip
   - 解压到 `%LOCALAPPDATA%\AdbTool\platform-tools`

3. **环境配置**
   - 添加路径到用户级 PATH 环境变量
   - 不修改系统级 PATH（避免权限问题）

4. **验证安装**
   - 执行 `adb version` 确认安装成功

### 模块二：设备连接管理 (device_service.py)
1. **设备列表获取**
   - 执行 `adb devices -l` 获取设备列表
   - 解析输出：序列号、状态、设备信息

2. **连接操作**
   - USB 连接：自动识别
   - Wi-Fi 连接：`adb connect <IP:PORT>`
   - 断开连接：`adb disconnect`

3. **ADB 服务管理**
   - `adb kill-server` 停止服务
   - `adb start-server` 启动服务
   - `adb restart-server` 重启服务（组合命令）

### 模块三：日志查看与筛选 (logcat_service.py)
1. **日志实时输出**
   - 使用 subprocess.Popen 启动 `adb logcat`
   - 使用 QThread 异步读取输出
   - 通过信号槽机制更新 UI

2. **日志筛选功能**
   - 按标签筛选: `adb logcat -s <TAG>`
   - 按级别筛选: `adb logcat *:<LEVEL>`
   - 按关键字筛选: 程序内部过滤
   - 按 PID 筛选: 先获取 PID，再 `adb logcat --pid=<PID>`

3. **日志操作**
   - 开始/停止日志
   - 清空日志窗口
   - 保存日志到文件
   - 快速筛选 Unity 日志按钮

## UI 布局设计

### 主窗口 (main_window.py)
```
┌─────────────────────────────────────────────────────────────┐
│  ADB 工具管理器                              [最小化][关闭]  │
├─────────────────────────────────────────────────────────────┤
│ [一键安装ADB] [刷新设备] [重启ADB服务]     状态: 已就绪    │
├──────────────────────┬──────────────────────────────────────┤
│     设备列表         │           日志面板                   │
│ ┌──────────────────┐ │ ┌──────────────────────────────────┐ │
│ │ 设备1 (在线)     │ │ │ 筛选: [级别▼] [Tag输入框]       │ │
│ │ 设备2 (离线)     │ │ │       [关键字输入框] [Unity日志] │ │
│ │                  │ │ ├──────────────────────────────────┤ │
│ │ [连接] [断开]    │ │ │                                  │ │
│ └──────────────────┘ │ │      日志输出区域                │ │
│                      │ │      (带滚动条)                  │ │
│                      │ │                                  │ │
│                      │ │                                  │ │
│                      │ ├──────────────────────────────────┤ │
│                      │ │ [开始] [停止] [清空] [保存日志]  │ │
│                      │ └──────────────────────────────────┘ │
└──────────────────────┴──────────────────────────────────────┘
```

## 开发任务清单

### 第一阶段：项目初始化
- [ ] 创建 Python 项目结构
- [ ] 配置 requirements.txt
- [ ] 创建基础 PyQt5 窗口框架

### 第二阶段：ADB 核心服务
- [ ] 实现 adb_service.py 基础类（subprocess 封装）
- [ ] 实现 adb_installer.py 安装服务
- [ ] 实现环境变量配置功能

### 第三阶段：设备管理
- [ ] 实现 device_service.py 设备服务
- [ ] 创建设备列表 UI (QListWidget)
- [ ] 实现设备连接/断开功能

### 第四阶段：日志功能
- [ ] 实现 logcat_service.py 日志服务 (QThread)
- [ ] 创建日志显示 UI (QTextEdit)
- [ ] 实现日志筛选功能
- [ ] 实现 Unity 日志快速筛选

### 第五阶段：完善与打包
- [ ] 添加错误处理和用户提示 (QMessageBox)
- [ ] 实现应用设置保存/加载 (JSON)
- [ ] UI 美化和 QSS 样式
- [ ] PyInstaller 打包为 exe

## 关键实现细节

### 1. ADB 进程执行 (process_utils.py)
```python
import asyncio
import subprocess

async def execute_adb(args: str, timeout: int = 30) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_shell(
        f"adb {args}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        return proc.returncode, stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "Timeout"
```

### 2. 日志实时输出 (QThread)
```python
from PyQt5.QtCore import QThread, pyqtSignal

class LogcatThread(QThread):
    log_received = pyqtSignal(str)
    
    def __init__(self, device_id: str = None, tag: str = None):
        super().__init__()
        self.device_id = device_id
        self.tag = tag
        self._running = True
    
    def run(self):
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.append("logcat")
        if self.tag:
            cmd.extend(["-s", self.tag])
        
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        for line in proc.stdout:
            if not self._running:
                break
            self.log_received.emit(line.strip())
    
    def stop(self):
        self._running = False
```

### 3. 环境变量配置 (env_utils.py)
```python
import winreg

def add_to_path(path: str) -> bool:
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_ALL_ACCESS
    )
    try:
        current_path, _ = winreg.QueryValueEx(key, "PATH")
        if path not in current_path:
            new_path = f"{path};{current_path}"
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
        return True
    finally:
        winreg.CloseKey(key)
```

### 4. 下载并解压 platform-tools
```python
import requests
import zipfile
import os

def download_and_extract(dest_dir: str) -> str:
    url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    zip_path = os.path.join(dest_dir, "platform-tools.zip")
    
    response = requests.get(url, stream=True)
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    
    os.remove(zip_path)
    return os.path.join(dest_dir, "platform-tools")
```

## 依赖列表 (requirements.txt)
```
PyQt5>=5.15.0
requests>=2.28.0
psutil>=5.9.0
```

## 打包配置 (PyInstaller)
```bash
pyinstaller --name "ADB工具管理器" \
    --onefile \
    --windowed \
    --icon=resources/icon.ico \
    adb_tool/main.py
```

## 预期成果
1. 可独立运行的 Windows 桌面应用程序 (exe)
2. 支持一键安装配置 ADB
3. 提供直观的设备管理界面
4. 强大的日志筛选功能，特别支持 Unity 开发
5. 良好的用户体验和错误提示

---

## 功能更新记录

### 2026-04-03 更新

#### 1. 日志性能优化

**问题**：程序运行时较为卡顿，尤其是点击[开始]读取日志后，经常出现未响应的情况。

**原因分析**：
- 主线程阻塞：设备检查在主线程同步执行
- 主线程处理过滤：每批日志都在主线程过滤
- 逐条插入日志：50条日志 = 50次 UI 渲染
- 全量重建显示：过滤时清空后逐条重新插入

**优化方案**：

| 优化项 | 修改位置 | 优化内容 |
|--------|----------|----------|
| 增大批次大小 | `logcat_service.py` | `_batch_size`: 50→100, `_batch_timeout`: 0.1s→0.15s |
| 定时器合并批次 | `logcat_service.py` | 新增 `_batch_timer`，日志先缓存后批量刷新（100ms间隔） |
| 批量 HTML 插入 | `main_window.py` | 使用 `insertHtml()` 批量插入，替代逐条 `insertText()` |
| 异步设备检查 | `main_window.py` | 使用 `QRunnable` + `QThreadPool` 后台检查设备 |
| 优化过滤刷新 | `main_window.py` | 批量构建 HTML 后使用 `setHtml()` 一次性更新 |

#### 2. 日志级别多选筛选

**功能**：日志级别筛选支持多选，可同时勾选多个级别（如同时显示 Info、Warning、Error）

**实现方式**：
- 使用自定义 `LevelMenu` (继承 `QMenu`) 替代 `QComboBox`
- 每个级别（Verbose/Debug/Info/Warning/Error/Fatal）为可勾选菜单项
- 客户端过滤（因为 ADB logcat 只支持单级别过滤）

#### 3. [全选] 功能

**功能**：级别菜单新增"全选"选项，点击可切换所有级别的勾选状态

**交互设计**：
- 点击"全选"，所有级别项实时变为勾选状态
- 再次点击"全选"，所有级别项实时变为取消勾选状态
- 位于菜单顶部，用分隔线与其他级别选项隔开

#### 4. 菜单关闭行为优化

**功能**：点击级别菜单中的选项后，菜单保持打开；只有点击菜单外部区域时才关闭并生效

**实现方式**：
- 自定义 `LevelMenu` 类，重写 `hide()` 方法
- 使用 `_ignore_next_close` 标志拦截关闭事件
- 通过事件过滤器检测鼠标点击位置

#### 5. 配置文件更新

**新增依赖**：
```python
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QRunnable, QThreadPool, QObject, QEvent
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QMouseEvent
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QComboBox, QSplitter,
    QMessageBox, QFileDialog, QGroupBox, QStatusBar,
    QDialog, QProgressBar, QApplication, QMenu, QAction,
    QToolButton
)
```

**新增类**：
- `DeviceCheckWorker` - 异步设备检查工作类
- `DeviceCheckSignals` - 设备检查信号类
- `LevelMenu` - 自定义级别选择菜单（支持多选、全选、延迟关闭）
