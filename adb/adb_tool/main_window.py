"""Main window for the ADB log viewer."""
from __future__ import annotations

import os
import sys
from collections import deque
from typing import Iterable, Optional

from PyQt5.QtCore import QEvent, QObject, QPoint, QRunnable, QThreadPool, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap, QPolygon, QTextCharFormat, QTextOption, QSyntaxHighlighter
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QStyle,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QAction,
    QMenu,
)

from adb_tool.models.device import AdbDevice, DeviceStatus
from adb_tool.models.log_entry import LogEntry, LogLevel
from adb_tool.services.adb_installer import AdbInstaller
from adb_tool.services.adb_service import AdbService
from adb_tool.services.device_service import DeviceService
from adb_tool.services.file_log_service import FileLogLoader
from adb_tool.services.logcat_service import LogcatService
from adb_tool.services.settings_service import SettingsService
from adb_tool.utils.logger import get_logger

logger = get_logger()


LEVEL_COLORS = {
    LogLevel.VERBOSE: "#8b949e",
    LogLevel.DEBUG: "#58a6ff",
    LogLevel.INFO: "#d0d7de",
    LogLevel.WARNING: "#f2cc60",
    LogLevel.ERROR: "#ff7b72",
    LogLevel.FATAL: "#ff4d6d",
    LogLevel.UNKNOWN: "#9aa4b2",
}

LEVEL_DOTS = {
    LogLevel.VERBOSE: "⚫",
    LogLevel.DEBUG: "🔵",
    LogLevel.INFO: "⚪",
    LogLevel.WARNING: "🟡",
    LogLevel.ERROR: "🔴",
    LogLevel.FATAL: "🔴",
    LogLevel.UNKNOWN: "⚫",
}


class DeviceCheckSignals(QObject):
    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)


class DeviceCheckWorker(QRunnable):
    def __init__(self, device_service: DeviceService):
        super().__init__()
        self.device_service = device_service
        self.signals = DeviceCheckSignals()

    def run(self):
        try:
            devices = self.device_service.get_devices()
            online_devices = [device for device in devices if device.is_online]
            self.signals.finished.emit(devices, online_devices)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class LevelMenu(QMenu):
    """Checkable level menu that stays open while toggling items."""

    selection_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ignore_next_close = False

    def event(self, event):
        if event.type() == QEvent.MouseButtonRelease:
            action = self.actionAt(event.pos())
            if action is not None and action.isEnabled():
                action.trigger()
                self._ignore_next_close = True
                self.selection_changed.emit(action)
                return True
        return super().event(event)

    def hide(self):
        if self._ignore_next_close:
            self._ignore_next_close = False
            return
        super().hide()


class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._formats = {}
        for level, color in LEVEL_COLORS.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self._formats[level.value] = fmt

    def highlightBlock(self, text: str):
        level = self._extract_level(text)
        fmt = self._formats.get(level)
        if fmt:
            self.setFormat(0, len(text), fmt)

    @staticmethod
    def _extract_level(text: str) -> Optional[str]:
        marker_pos = text.find("] ")
        if marker_pos > 0:
            start = text.rfind("[", 0, marker_pos)
            if start >= 0 and marker_pos - start == 2:
                return text[start + 1 : marker_pos]
        # Raw logcat lines usually keep the level after pid/tid columns.
        parts = text.split(None, 5)
        if len(parts) >= 5 and parts[4] in {"V", "D", "I", "W", "E", "F", "S", "?"}:
            return parts[4]
        return None


class InstallDialog(QDialog):
    def __init__(self, installer: AdbInstaller, parent=None):
        super().__init__(parent)
        self.installer = installer
        self.setWindowTitle("安装 ADB")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.status_label = QLabel("准备安装 ADB...")
        self.status_label.setObjectName("dialogTitle")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        self.close_button = QPushButton("关闭")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button, alignment=Qt.AlignRight)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self.start_install)

    def start_install(self):
        def progress_callback(message: str, percent: int):
            self.status_label.setText(message)
            self.progress_bar.setValue(percent)
            QApplication.processEvents()

        try:
            success, message = self.installer.install(progress_callback)
            self.progress_bar.setValue(100 if success else 0)
            self.status_label.setText("安装完成" if success else "安装失败")
            self.status_label.setProperty("state", "ok" if success else "error")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            self.detail_label.setText(message)
            self.close_button.setEnabled(True)
        except Exception as exc:
            self.status_label.setText("安装失败")
            self.detail_label.setText(f"发生错误: {exc}")
            self.close_button.setEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.adb_service = AdbService()
        self.installer = AdbInstaller(self.adb_service)
        self.device_service = DeviceService(self.adb_service)
        self.logcat_service = LogcatService(self.adb_service)
        self.settings_service = SettingsService()

        max_entries = max(100000, self.settings_service.settings.log_buffer_size)
        self._log_entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._current_device: Optional[AdbDevice] = None
        self._file_loader: Optional[FileLogLoader] = None
        self._thread_pool = QThreadPool.globalInstance()
        self._display_limit = 20000
        self._source_name = "实时日志"

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self._apply_filter_now)

        self._setup_ui()
        self._apply_tooltips()
        self._connect_signals()
        self._load_styles()
        self._check_adb()

    def _setup_ui(self):
        self.setWindowTitle("ADB 日志查看器")
        self.setWindowIcon(QIcon(self._resource_path("tubiao.ico")))
        self.setMinimumSize(1150, 780)
        self.resize(1150, 780)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 6)
        main_layout.setSpacing(6)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._create_device_panel())
        splitter.addWidget(self._create_log_panel())
        splitter.setSizes([240, 1000])
        main_layout.addWidget(splitter, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("就绪")

    def _create_device_panel(self) -> QWidget:
        group = QGroupBox("设备")
        group.setMinimumWidth(225)
        group.setMaximumWidth(300)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(7)

        self.status_label = QLabel("ADB 状态: 检查中...")
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        device_actions = QFrame()
        device_actions.setObjectName("deviceActions")
        actions_layout = QGridLayout(device_actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setHorizontalSpacing(6)
        actions_layout.setVerticalSpacing(6)

        self.install_btn = QPushButton("安装 ADB")
        self.refresh_btn = QPushButton("刷新设备")
        self.restart_btn = QPushButton("重启 ADB")
        self._set_button_icon(self.install_btn, QStyle.SP_DialogSaveButton)
        self._set_button_icon(self.refresh_btn, QStyle.SP_BrowserReload)
        self._set_button_icon(self.restart_btn, QStyle.SP_BrowserReload)
        for button in (self.install_btn, self.refresh_btn, self.restart_btn):
            button.setMinimumHeight(29)
        actions_layout.addWidget(self.install_btn, 0, 0, 1, 2)
        actions_layout.addWidget(self.refresh_btn, 1, 0)
        actions_layout.addWidget(self.restart_btn, 1, 1)
        layout.addWidget(device_actions)

        self.device_list = QListWidget()
        self.device_list.setAlternatingRowColors(True)
        layout.addWidget(self.device_list, 1)

        connect_grid = QGridLayout()
        connect_grid.setHorizontalSpacing(8)
        connect_grid.setVerticalSpacing(8)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP:端口，例如 192.168.1.8:5555")
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")
        self._set_button_icon(self.connect_btn, QStyle.SP_DialogApplyButton)
        self._set_button_icon(self.disconnect_btn, QStyle.SP_DialogCancelButton)
        connect_grid.addWidget(self.ip_input, 0, 0, 1, 2)
        connect_grid.addWidget(self.connect_btn, 1, 0)
        connect_grid.addWidget(self.disconnect_btn, 1, 1)
        layout.addLayout(connect_grid)

        return group

    def _create_log_panel(self) -> QWidget:
        group = QGroupBox("日志")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(6, 5, 6, 5)
        toolbar_layout.setSpacing(6)

        self.level_menu = LevelMenu(self)
        self.level_actions = {}
        self.select_all_action = QAction("全部级别", self.level_menu)
        self.select_all_action.setCheckable(True)
        self.select_all_action.setChecked(True)
        self.level_menu.addAction(self.select_all_action)
        self.level_menu.addSeparator()
        for level in (LogLevel.VERBOSE, LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL, LogLevel.UNKNOWN):
            action = QAction(self._level_action_text(level, True), self.level_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.setData(level)
            action.setToolTip(self._level_tooltip(level))
            action.setStatusTip(self._level_tooltip(level))
            self.level_menu.addAction(action)
            self.level_actions[level] = action

        self.level_btn = QToolButton()
        self.level_btn.setText("级别: 全部")
        self.level_btn.setMenu(self.level_menu)
        self.level_btn.setPopupMode(QToolButton.InstantPopup)
        self.level_btn.setMinimumWidth(100)
        self.level_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        toolbar_layout.addWidget(self.level_btn)

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Tag")
        self.tag_input.setMinimumWidth(55)
        self.tag_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        toolbar_layout.addWidget(self.tag_input, 2)

        self.unity_btn = QPushButton("Unity")
        self._set_button_icon(self.unity_btn, QStyle.SP_FileDialogDetailedView)
        self.unity_btn.setMinimumHeight(29)
        self.unity_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        toolbar_layout.addWidget(self.unity_btn)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("关键字")
        self.keyword_input.setMinimumWidth(70)
        self.keyword_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        toolbar_layout.addWidget(self.keyword_input, 3)

        self.auto_scroll_checkbox = QCheckBox("自动滚动")
        self.auto_scroll_checkbox.setChecked(self.settings_service.settings.auto_scroll_log)
        self.auto_scroll_checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        toolbar_layout.addWidget(self.auto_scroll_checkbox)

        self.open_file_btn = QPushButton("打开日志文件")
        self.start_log_btn = QPushButton("开始")
        self.stop_log_btn = QPushButton("停止")
        self.clear_log_btn = QPushButton("清空")
        self.save_log_btn = QPushButton("保存")
        self.start_log_btn.setObjectName("primaryButton")
        self.stop_log_btn.setObjectName("dangerButton")
        self.stop_log_btn.setEnabled(False)
        self._set_button_icon(self.open_file_btn, QStyle.SP_DialogOpenButton)
        self.start_log_btn.setIcon(self._colored_icon("play", QColor("#ffffff")))
        self._stop_icon_disabled = self._colored_icon("stop", QColor("#cf222e"))
        self._stop_icon_active = self._colored_icon("stop", QColor("#ffffff"))
        self.stop_log_btn.setIcon(self._stop_icon_disabled)
        self._set_button_icon(self.clear_log_btn, QStyle.SP_DialogResetButton)
        self._set_button_icon(self.save_log_btn, QStyle.SP_DialogSaveButton)
        toolbar_layout.addStretch(1)
        for button in (self.start_log_btn, self.stop_log_btn, self.clear_log_btn, self.save_log_btn, self.open_file_btn):
            button.setMinimumHeight(29)
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            toolbar_layout.addWidget(button)

        layout.addWidget(toolbar)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.log_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self._force_log_view_colors()
        self.log_text.document().setMaximumBlockCount(self._display_limit)
        self.highlighter = LogHighlighter(self.log_text.document())
        layout.addWidget(self.log_text, 1)

        footer = QFrame()
        footer.setObjectName("logFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(8, 4, 8, 4)
        self.counter_label = QLabel("0 行")
        self.source_label = QLabel(self._source_name)
        self.load_progress = QProgressBar()
        self.load_progress.setRange(0, 100)
        self.load_progress.setValue(0)
        self.load_progress.setTextVisible(False)
        self.load_progress.setMaximumWidth(160)
        self.load_progress.hide()
        footer_layout.addWidget(self.source_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.load_progress)
        footer_layout.addWidget(self.counter_label)
        self.help_btn = QToolButton()
        self.help_btn.setObjectName("helpButton")
        self.help_btn.setText("!")
        self.help_btn.setToolTip("如遇问题，联系范博年")
        self.help_btn.setFixedSize(22, 22)
        footer_layout.addWidget(self.help_btn)
        layout.addWidget(footer)

        return group

    def _set_button_icon(self, button: QPushButton, standard_icon: QStyle.StandardPixmap):
        button.setIcon(self.style().standardIcon(standard_icon))
        button.setIconSize(QSize(15, 15))

    def _colored_icon(self, shape: str, color: QColor) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        if shape == "play":
            painter.drawPolygon(
                QPolygon([
                    QPoint(6, 4),
                    QPoint(6, 14),
                    QPoint(14, 9),
                ])
            )
        else:
            painter.drawRoundedRect(5, 5, 10, 10, 2, 2)
        painter.end()
        icon = QIcon()
        icon.addPixmap(pixmap, QIcon.Normal)
        icon.addPixmap(pixmap, QIcon.Disabled)
        return icon

    def _level_action_text(self, level: LogLevel, checked: bool) -> str:
        dot = LEVEL_DOTS.get(level, "⚫")
        return f"{level.display_name}  {dot}"

    def _refresh_level_action_texts(self):
        self.select_all_action.setText("全部级别")
        for level, action in self.level_actions.items():
            action.setText(self._level_action_text(level, action.isChecked()))

    def _connect_signals(self):
        self.install_btn.clicked.connect(self._on_install_clicked)
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.restart_btn.clicked.connect(self._restart_adb_server)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.device_list.currentRowChanged.connect(self._on_device_selected)
        self.device_list.itemDoubleClicked.connect(self._on_device_double_clicked)

        self.open_file_btn.clicked.connect(self._open_log_file)
        self.start_log_btn.clicked.connect(self._start_logcat)
        self.stop_log_btn.clicked.connect(self._stop_logcat)
        self.clear_log_btn.clicked.connect(self._clear_log)
        self.save_log_btn.clicked.connect(self._save_log)
        self.unity_btn.clicked.connect(self._filter_unity_logs)

        self.tag_input.textChanged.connect(self._schedule_filter)
        self.keyword_input.textChanged.connect(self._schedule_filter)
        self.auto_scroll_checkbox.toggled.connect(self._on_auto_scroll_toggled)
        self.level_menu.selection_changed.connect(self._on_level_selection_changed)

        self.logcat_service.log_batch_received.connect(self._on_log_batch_received, Qt.QueuedConnection)
        self.logcat_service.started.connect(self._on_logcat_started)
        self.logcat_service.stopped.connect(self._on_logcat_stopped)
        self.logcat_service.error.connect(self._on_logcat_error)
        self.help_btn.clicked.connect(self._show_help_tip)

    def _apply_tooltips(self):
        self.install_btn.setToolTip("下载并安装 Android platform-tools，让软件可以使用 adb。")
        self.refresh_btn.setToolTip("重新扫描当前连接的 Android 设备。")
        self.restart_btn.setToolTip("重启 ADB 服务，常用于设备识别异常、连接卡住时。")
        self.ip_input.setToolTip("输入无线调试设备地址，例如 192.168.1.8:5555。")
        self.connect_btn.setToolTip("连接输入框里的无线调试设备。")
        self.disconnect_btn.setToolTip("断开当前选中的无线设备；未选中无线设备时断开全部无线连接。")
        self.device_list.setToolTip("显示当前识别到的设备，双击在线设备可直接开始读取日志。")

        self.level_btn.setToolTip("选择要显示的日志级别。")
        self.select_all_action.setToolTip("一键勾选或取消所有日志级别。")
        self.select_all_action.setStatusTip("一键勾选或取消所有日志级别。")
        for level, action in self.level_actions.items():
            tip = self._level_tooltip(level)
            action.setToolTip(tip)
            action.setStatusTip(tip)

        self.tag_input.setToolTip("按日志 Tag 筛选，例如 Unity、ActivityManager。")
        self.unity_btn.setToolTip("快速把 Tag 设置为 Unity，用于查看 Unity 相关日志。")
        self.keyword_input.setToolTip("按日志内容里的关键字筛选。")
        self.auto_scroll_checkbox.setToolTip("勾选后，新日志出现时自动滚动到底部；取消后可以停在当前位置查看旧日志。")
        self.start_log_btn.setToolTip("开始读取当前设备的实时 logcat 日志。")
        self.stop_log_btn.setToolTip("停止读取实时日志。")
        self.clear_log_btn.setToolTip("清空当前显示和内存缓存的日志。")
        self.save_log_btn.setToolTip("把当前缓存的日志保存到文本文件。")
        self.open_file_btn.setToolTip("打开本地日志文件进行查看，适合查看较大的日志文件尾部内容。")

    def _show_help_tip(self):
        QToolTip.showText(
            self.help_btn.mapToGlobal(QPoint(0, self.help_btn.height() + 4)),
            "如遇问题，联系范博年",
            self.help_btn,
        )

    def _level_tooltip(self, level: LogLevel) -> str:
        descriptions = {
            LogLevel.VERBOSE: "显示最详细的调试日志。",
            LogLevel.DEBUG: "显示调试日志。",
            LogLevel.INFO: "显示普通信息日志。",
            LogLevel.WARNING: "显示警告日志。",
            LogLevel.ERROR: "显示错误日志。",
            LogLevel.FATAL: "显示严重错误日志。",
            LogLevel.UNKNOWN: "显示无法解析出级别的日志行。",
        }
        return descriptions.get(level, "显示该级别的日志。")

    def _load_styles(self):
        try:
            style_path = self._resource_path("adb_tool/resources/styles.qss")
            with open(style_path, "r", encoding="utf-8") as style_file:
                self.setStyleSheet(style_file.read())
        except Exception as exc:
            logger.warning(f"加载样式失败: {exc}")
        self._force_log_view_colors()

    @staticmethod
    def _resource_path(relative_path: str) -> str:
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, relative_path)

    def _force_log_view_colors(self):
        if not hasattr(self, "log_text"):
            return
        palette = self.log_text.palette()
        for role in (QPalette.Base, QPalette.Window):
            palette.setColor(role, QColor("#000000"))
        palette.setColor(QPalette.Text, QColor("#d7dde5"))
        palette.setColor(QPalette.Highlight, QColor("#264f78"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.log_text.setPalette(palette)
        self.log_text.viewport().setAutoFillBackground(True)
        viewport_palette = self.log_text.viewport().palette()
        viewport_palette.setColor(QPalette.Window, QColor("#000000"))
        viewport_palette.setColor(QPalette.Base, QColor("#000000"))
        self.log_text.viewport().setPalette(viewport_palette)

    def _check_adb(self):
        if self.installer.is_installed():
            version = self.adb_service.get_version()
            suffix = f" v{version}" if version else ""
            self.status_label.setText(f"ADB 状态: 已可用{suffix}")
            self.install_btn.setText("重新安装 ADB")
            self._refresh_devices()
        else:
            self.status_label.setText("ADB 状态: 未检测到可用 adb")
            self.install_btn.setText("安装 ADB")

    def _on_install_clicked(self):
        dialog = InstallDialog(self.installer, self)
        dialog.exec_()
        self._check_adb()

    def _refresh_devices(self):
        self.device_list.clear()
        devices = self.device_service.get_devices()
        for device in devices:
            item = QListWidgetItem(device.display_name)
            item.setData(Qt.UserRole, device.serial)
            item.setToolTip(self._device_tooltip(device))
            if device.is_online:
                item.setForeground(QColor("#1a7f37"))
            elif device.status == DeviceStatus.UNAUTHORIZED:
                item.setForeground(QColor("#9a6700"))
            else:
                item.setForeground(QColor("#cf222e"))
            self.device_list.addItem(item)
        self.statusBar().showMessage(f"发现 {len(devices)} 个设备")

    @staticmethod
    def _device_tooltip(device: AdbDevice) -> str:
        rows = [f"序列号: {device.serial}", f"状态: {device.status.value}"]
        if device.model:
            rows.append(f"型号: {device.model}")
        if device.product:
            rows.append(f"产品: {device.product}")
        if device.transport_id is not None:
            rows.append(f"Transport ID: {device.transport_id}")
        return "\n".join(rows)

    def _restart_adb_server(self):
        self.statusBar().showMessage("正在重启 ADB 服务...")
        success, message = self.device_service.restart_adb_server()
        if success:
            self.statusBar().showMessage(message)
            QTimer.singleShot(1000, self._refresh_devices)
        else:
            QMessageBox.warning(self, "错误", message)
            self.statusBar().showMessage("重启失败")

    def _on_connect_clicked(self):
        address = self.ip_input.text().strip()
        if not address:
            QMessageBox.warning(self, "提示", "请输入设备地址")
            return
        success, message = self.device_service.connect(address)
        if success:
            self.statusBar().showMessage(message)
            self._refresh_devices()
        else:
            QMessageBox.warning(self, "连接失败", message)

    def _on_disconnect_clicked(self):
        current_item = self.device_list.currentItem()
        address = None
        if current_item:
            serial = current_item.data(Qt.UserRole)
            if ":" in serial:
                address = serial
        _, message = self.device_service.disconnect(address)
        self.statusBar().showMessage(message)
        self._refresh_devices()

    def _on_device_selected(self, row: int):
        self._current_device = None
        if row >= 0:
            item = self.device_list.item(row)
            self._current_device = self.device_service.get_device_by_serial(item.data(Qt.UserRole))

    def _on_device_double_clicked(self, item: QListWidgetItem):
        serial = item.data(Qt.UserRole)
        self._current_device = self.device_service.get_device_by_serial(serial)
        if self._current_device and self._current_device.is_online:
            if self.logcat_service.is_running:
                self._stop_logcat()
            self._start_logcat()

    def _start_logcat(self):
        self.start_log_btn.setEnabled(False)
        self.start_log_btn.setText("启动中")
        self.stop_log_btn.setEnabled(False)
        self.statusBar().showMessage("正在检查设备...")
        self.setCursor(Qt.WaitCursor)
        worker = DeviceCheckWorker(self.device_service)
        worker.signals.finished.connect(self._on_device_check_finished)
        worker.signals.error.connect(self._on_device_check_error)
        self._thread_pool.start(worker)

    def _on_device_check_finished(self, devices, online_devices):
        try:
            if not online_devices:
                self.start_log_btn.setEnabled(True)
                self.start_log_btn.setText("开始")
                self.unsetCursor()
                message = "没有发现设备"
                if devices:
                    message = "发现设备，但没有在线设备。请确认设备已授权 USB 调试。"
                QMessageBox.warning(self, "提示", message)
                return

            device_id = self._current_device.serial if self._current_device and self._current_device.is_online else online_devices[0].serial
            tag = self.tag_input.text().strip() or None
            self._source_name = f"logcat: {device_id}"
            self.source_label.setText(self._source_name)
            self._clear_log(reset_source=False)
            self.logcat_service.start(device_id=device_id, tag=tag)
        except Exception as exc:
            logger.error(f"启动 logcat 失败: {exc}")
            QMessageBox.critical(self, "错误", f"启动日志失败: {exc}")
            self.start_log_btn.setEnabled(True)
            self.start_log_btn.setText("开始")
            self.unsetCursor()

    def _on_device_check_error(self, error_msg: str):
        QMessageBox.critical(self, "错误", f"设备检查失败: {error_msg}")
        self.start_log_btn.setEnabled(True)
        self.start_log_btn.setText("开始")
        self.unsetCursor()

    def _stop_logcat(self):
        self.logcat_service.stop()

    def _on_logcat_started(self):
        self.unsetCursor()
        self.start_log_btn.setEnabled(False)
        self.start_log_btn.setText("运行中")
        self.stop_log_btn.setEnabled(True)
        self.stop_log_btn.setIcon(self._stop_icon_active)
        self.statusBar().showMessage("日志监控中...")

    def _on_logcat_stopped(self):
        self.start_log_btn.setEnabled(True)
        self.start_log_btn.setText("开始")
        self.stop_log_btn.setEnabled(False)
        self.stop_log_btn.setIcon(self._stop_icon_disabled)
        self.statusBar().showMessage("日志已停止")

    def _on_logcat_error(self, message: str):
        self.statusBar().showMessage(message)

    def _open_log_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "打开日志文件",
            "",
            "日志文件 (*.txt *.log);;所有文件 (*.*)",
        )
        if not filepath:
            return
        if self.logcat_service.is_running:
            self._stop_logcat()
        if self._file_loader and self._file_loader.isRunning():
            self._file_loader.stop()

        self._source_name = filepath
        self.source_label.setText(filepath)
        self._clear_log(reset_source=False)
        self.load_progress.show()
        self.load_progress.setValue(0)
        self.statusBar().showMessage("正在加载日志文件尾部内容...")

        self._file_loader = FileLogLoader(filepath, max_bytes=16 * 1024 * 1024, batch_size=1000)
        self._file_loader.batch_loaded.connect(self._on_log_batch_received, Qt.QueuedConnection)
        self._file_loader.progress_changed.connect(self._on_file_load_progress)
        self._file_loader.finished_loading.connect(self._on_file_load_finished)
        self._file_loader.error.connect(self._on_file_load_error)
        self._file_loader.start()

    def _on_file_load_progress(self, percent: int):
        self.load_progress.setValue(percent)

    def _on_file_load_finished(self, total_lines: int, truncated: bool):
        self.load_progress.hide()
        note = "，仅加载尾部 16MB" if truncated else ""
        self.statusBar().showMessage(f"已加载 {total_lines} 行{note}")
        self._update_counter()

    def _on_file_load_error(self, message: str):
        self.load_progress.hide()
        QMessageBox.warning(self, "读取失败", message)
        self.statusBar().showMessage("日志文件读取失败")

    def _on_log_batch_received(self, entries: list):
        if not entries:
            return
        self._log_entries.extend(entries)
        filtered = [entry for entry in entries if self._entry_matches(entry)]
        if filtered:
            self._append_log_batch(filtered)
        self._update_counter()

    def _append_log_batch(self, entries: Iterable[LogEntry]):
        text = "\n".join(entry.formatted_line for entry in entries)
        if not text:
            return
        at_bottom = self.log_text.verticalScrollBar().value() >= self.log_text.verticalScrollBar().maximum() - 4
        self.log_text.appendPlainText(text)
        if self.auto_scroll_checkbox.isChecked() or at_bottom:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _schedule_filter(self):
        self._filter_timer.start(220)

    def _apply_filter_now(self):
        selected = []
        hidden_count = 0
        for entry in self._log_entries:
            if self._entry_matches(entry):
                selected.append(entry.formatted_line)
                if len(selected) > self._display_limit:
                    hidden_count += 1
                    selected.pop(0)
        self.log_text.setPlainText("\n".join(selected))
        if self.auto_scroll_checkbox.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        suffix = f"，显示最近 {self._display_limit} 行" if hidden_count else ""
        self.statusBar().showMessage(f"过滤完成: {len(selected)} 行{suffix}")
        self._update_counter()

    def _entry_matches(self, entry: LogEntry) -> bool:
        return entry.matches_filter(
            tag=self.tag_input.text().strip() or None,
            levels=self._get_selected_levels(),
            keyword=self.keyword_input.text().strip() or None,
        )

    def _get_selected_levels(self):
        return [level for level, action in self.level_actions.items() if action.isChecked()]

    def _on_level_selection_changed(self, action):
        if action == self.select_all_action:
            checked = self.select_all_action.isChecked()
            for action in self.level_actions.values():
                action.setChecked(checked)
        else:
            selected_count = len(self._get_selected_levels())
            self.select_all_action.setChecked(selected_count == len(self.level_actions))
        self._refresh_level_action_texts()
        self._update_level_button()
        self._schedule_filter()

    def _update_level_button(self):
        selected = self._get_selected_levels()
        if len(selected) == len(self.level_actions):
            text = "级别: 全部"
        elif not selected:
            text = "级别: 无"
        elif len(selected) <= 2:
            text = "级别: " + ", ".join(level.value for level in selected)
        else:
            text = f"级别: {len(selected)} 项"
        self.level_btn.setText(text)

    def _on_auto_scroll_toggled(self, checked: bool):
        self.settings_service.settings.auto_scroll_log = checked
        if checked:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _filter_unity_logs(self):
        self.tag_input.setText("Unity")
        if not self.logcat_service.is_running and not self._log_entries:
            self._start_logcat()

    def _clear_log(self, reset_source: bool = True):
        self.log_text.clear()
        self._log_entries.clear()
        self.logcat_service.clear_entries()
        if reset_source:
            self._source_name = "实时日志"
            self.source_label.setText(self._source_name)
        self._update_counter()

    def _save_log(self):
        if not self._log_entries:
            QMessageBox.information(self, "提示", "没有日志可保存")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "保存日志",
            "logcat.txt",
            "文本文件 (*.txt);;所有文件 (*.*)",
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as output:
                for entry in self._log_entries:
                    output.write(entry.raw_line + "\n")
            self.statusBar().showMessage(f"日志已保存: {filepath}")
        except Exception as exc:
            QMessageBox.warning(self, "错误", f"保存日志失败: {exc}")

    def _update_counter(self):
        self.counter_label.setText(f"{len(self._log_entries)} 行缓存")

    def closeEvent(self, event):
        if self.logcat_service.is_running:
            self.logcat_service.stop()
        if self._file_loader and self._file_loader.isRunning():
            self._file_loader.stop()
            self._file_loader.wait(1500)
        self.settings_service.save()
        event.accept()
