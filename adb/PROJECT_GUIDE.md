# ADB 工具管理器 - 项目文档

## 项目概述

一个基于 PyQt5 开发的 Windows 桌面应用程序，用于简化 Android 设备的 ADB 操作，提供一键安装、设备管理、日志查看等功能。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 开发语言 | Python 3.10+ |
| UI 框架 | PyQt5 |
| 打包工具 | PyInstaller |
| 核心依赖 | PyQt5, requests, psutil |

---

## 项目结构

```
adb_tool/
├── main.py                      # 程序入口
├── main_window.py               # 主窗口 UI（核心文件）
├── models/
│   ├── device.py               # 设备数据模型
│   ├── log_entry.py            # 日志条目模型（含过滤逻辑）
│   └── settings.py             # 应用设置模型
├── services/
│   ├── adb_service.py          # ADB 核心服务（执行命令）
│   ├── adb_installer.py        # ADB 安装服务（下载、解压）
│   ├── device_service.py       # 设备管理服务（连接、断开）
│   ├── logcat_service.py       # 日志服务（批量读取）
│   └── settings_service.py     # 设置管理（JSON 持久化）
├── utils/
│   ├── env_utils.py            # 环境变量工具（注册表操作）
│   ├── logger.py               # 日志记录器
│   └── process_utils.py        # 进程辅助工具
└── resources/
    └── styles.qss              # Qt 样式表
```

---

## 核心功能

### 1. ADB 安装与配置
- 自动检测 ADB 是否已安装
- 一键下载 Google 官方 platform-tools
- 解压到 `%LOCALAPPDATA%\AdbTool\platform-tools`
- 自动配置用户级 PATH 环境变量

### 2. 设备管理
- 显示设备列表（在线/离线/未授权状态）
- USB 设备自动识别
- Wi-Fi 连接：`adb connect <IP:PORT>`
- 断开连接、重启 ADB 服务

### 3. 日志查看（Logcat）
- 实时日志监控
- **多级别筛选**：支持同时选择多个级别（Verbose/Debug/Info/Warning/Error/Fatal）
- Tag 筛选
- 关键字筛选
- Unity 日志快速筛选
- 日志保存到文件

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────────┐
│         Views (main_window.py)      │  UI 层：PyQt5 组件
├─────────────────────────────────────┤
│         Services                    │  业务层：服务类
│  - AdbService                       │
│  - LogcatService                    │
│  - DeviceService                    │
├─────────────────────────────────────┤
│         Models                      │  数据层：数据模型
│  - LogEntry                         │
│  - AdbDevice                        │
└─────────────────────────────────────┘
```

### 多线程架构

| 线程/组件 | 用途 | 实现方式 |
|-----------|------|----------|
| 主线程 | UI 渲染、用户交互 | PyQt5 主事件循环 |
| LogcatThread | 读取 ADB 日志 | QThread + subprocess.Popen |
| DeviceCheckWorker | 异步检查设备 | QRunnable + QThreadPool |
| 批量刷新定时器 | 合并日志批次 | QTimer |

---

## 关键实现要点

### 1. 日志性能优化（重要）

**问题**：大量日志会导致 UI 卡顿、未响应。

**优化方案**：

```python
# logcat_service.py
class LogcatThread(QThread):
    _batch_size = 100      # 增大批次（原始50）
    _batch_timeout = 0.15   # 批次超时

class LogcatService(QObject):
    def __init__(self):
        self._batch_timer = QTimer()      # 定时器合并批次
        self._batch_timer.timeout.connect(self._flush_pending_batch)
        self._batch_flush_interval = 100   # 100ms 刷新间隔
```

**主窗口批量插入**：
```python
# main_window.py - 使用 HTML 批量插入
def _append_log_batch(self, entries):
    html_parts = []
    for entry in entries:
        color = self._get_log_color(entry.level)
        escaped_text = entry.formatted_line.replace('&', '&amp;')...
        html_parts.append(f'<span style="color:{color}">{escaped_text}</span>')
    batch_html = '<br>'.join(html_parts) + '<br>'
    cursor.insertHtml(batch_html)  # 一次性插入
```

### 2. 自定义级别菜单（LevelMenu）

支持多选、全选、延迟关闭的自定义 QMenu。

```python
class LevelMenu(QMenu):
    """支持多选和延迟关闭的级别选择菜单"""
    
    def __init__(self):
        super().__init__()
        self._ignore_next_close = False
        self._select_all_action = None
    
    def event(self, event):
        # 拦截鼠标点击，手动触发 action
        if event.type() == QEvent.MouseButtonRelease:
            action = self.actionAt(event.pos())
            if action == self._select_all_action:
                self._handle_select_all(action)  # 全选逻辑
            else:
                action.trigger()
            self._ignore_next_close = True
            return True
        return super().event(event)
    
    def hide(self):
        # 点击选项时阻止关闭，只有点击外部才关闭
        if self._ignore_next_close:
            self._ignore_next_close = False
            return
        super().hide()
```

**菜单结构**：
```
┌─────────────────────┐
│ ☑ 全选              │  ← 点击切换所有级别
│─────────────────────│
│ ☑ Verbose          │
│ ☑ Debug            │
│ ☑ Info             │
│ ☑ Warning          │
│ ☑ Error            │
│ ☑ Fatal            │
└─────────────────────┘
```

### 3. 异步设备检查

避免启动日志时 UI 冻结：

```python
class DeviceCheckWorker(QRunnable):
    def __init__(self, device_service):
        super().__init__()
        self.device_service = device_service
        self.signals = DeviceCheckSignals()
    
    def run(self):
        devices = self.device_service.get_devices()
        online = [d for d in devices if d.is_online]
        self.signals.finished.emit(devices, online)

# 主窗口使用
def _start_logcat(self):
    worker = DeviceCheckWorker(self.device_service)
    worker.signals.finished.connect(self._on_device_check_finished)
    QThreadPool.globalInstance().start(worker)
```

### 4. 日志多级别过滤

```python
# log_entry.py
def matches_filter(
    self,
    tag: Optional[str] = None,
    level: Optional[LogLevel] = None,
    levels: Optional[List[LogLevel]] = None,  # 支持多级别
    keyword: Optional[str] = None,
    pid: Optional[int] = None
) -> bool:
    if levels and self.level not in levels:
        return False  # 在 levels 列表中则通过
    # ...
```

---

## 依赖导入（重要）

```python
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QThread, QRunnable, 
    QThreadPool, QObject, QEvent
)
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QTextCursor, QMouseEvent
)
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QComboBox, QSplitter,
    QMessageBox, QFileDialog, QGroupBox, QStatusBar,
    QDialog, QProgressBar, QApplication, QMenu, QAction,
    QToolButton
)
```

---

## 打包配置

PyInstaller 配置文件：`ADB工具管理器.spec`

```python
a = Analysis(
    ['adb_tool\\main.py'],
    # ...
)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='ADB工具管理器',
    console=False,  # 无控制台窗口
    # ...
)
```

**打包命令**：
```bash
python -m PyInstaller "ADB工具管理器.spec" --clean
```

**输出位置**：`dist/ADB工具管理器.exe`

---

## 注意事项

### 1. 多线程安全
- 所有 UI 更新必须在主线程
- 使用 `Qt.QueuedConnection` 传递信号
- 后台线程只做数据处理，不直接操作 UI

### 2. 内存管理
- 日志数量限制：`self._max_entries = 10000`
- 超过限制时裁剪旧数据：`self._entries = self._entries[-5000:]`

### 3. 编码处理
- subprocess 使用 `encoding='utf-8', errors='ignore'`
- HTML 特殊字符转义：`replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')`

### 4. Windows 特定
- 使用 `subprocess.CREATE_NO_WINDOW` 隐藏子进程窗口
- 注册表操作使用 `winreg` 模块

---

## 开发建议

### 添加新功能
1. 在 `services/` 中添加服务类
2. 在 `models/` 中添加数据模型
3. 在 `main_window.py` 中连接信号槽

### 调试技巧
```python
# 启用详细日志
logger.info("调试信息")
logger.error("错误信息")
```

### 测试清单
- [ ] ADB 安装流程
- [ ] 设备连接/断开
- [ ] 日志实时显示
- [ ] 级别多选筛选
- [ ] 全选功能
- [ ] 菜单延迟关闭
- [ ] 关键字筛选
- [ ] 日志保存

---

## 文件位置

| 文件 | 路径 |
|------|------|
| 源代码 | `e:\ai_pj\adb\adb_tool\` |
| 打包配置 | `e:\ai_pj\adb\ADB工具管理器.spec` |
| 项目计划 | `e:\ai_pj\adb\PLAN.md` |
| 可执行文件 | `e:\ai_pj\adb\dist\ADB工具管理器.exe` |
