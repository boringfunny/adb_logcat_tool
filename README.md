# ADB Logcat Tool / ADB 日志查看器

一个面向 Windows 的 ADB 日志查看与设备管理工具，基于 Python + PyQt5 构建，可打包为独立 exe。它提供 ADB 安装、设备刷新、无线连接、实时 logcat 查看、日志级别筛选、Tag/关键字筛选、本地大日志文件查看与日志保存等功能，适合 Android 与 Unity 开发调试场景。

ADB Logcat Tool is a Windows desktop utility for Android device management and logcat viewing. Built with Python and PyQt5, it can be packaged as a standalone executable. It supports ADB setup, device discovery, wireless ADB connection, real-time logcat streaming, level/tag/keyword filtering, large local log file viewing, and log export. It is especially useful for Android and Unity debugging workflows.

## 功能特点 / Features

- ADB 安装与检测：支持检测本机 ADB，并可下载 Android platform-tools。
- 设备管理：刷新设备列表、重启 ADB 服务、连接/断开无线调试设备。
- 实时日志查看：读取指定设备的 `adb logcat` 输出。
- 多级别筛选：支持 Verbose、Debug、Info、Warning、Error、Fatal、Unknown。
- 快速 Unity 筛选：一键将 Tag 设置为 `Unity`。
- Tag 与关键字筛选：快速定位目标日志。
- 大日志优化：日志缓存上限为 100,000 行，界面显示上限保持 20,000 行，兼顾保存范围与界面流畅度。
- 本地日志文件查看：支持打开较大的日志文件，并优先加载尾部内容。
- 深色日志显示区：黑色背景与级别颜色高亮，便于观察警告和错误。
- 工具提示：主要按钮与控件提供中文悬停说明。
- 可打包 exe：使用 PyInstaller 生成 Windows 可执行文件。

- ADB setup and detection: checks local ADB and can download Android platform-tools.
- Device management: refresh devices, restart ADB server, connect/disconnect wireless debugging devices.
- Real-time logcat: streams `adb logcat` from a selected device.
- Multi-level filtering: Verbose, Debug, Info, Warning, Error, Fatal, and Unknown.
- Unity shortcut: quickly filters logs by the `Unity` tag.
- Tag and keyword filtering: helps locate target logs quickly.
- Large-log optimization: keeps up to 100,000 cached entries while rendering up to 20,000 visible lines for smoother UI.
- Local log file viewer: opens large log files and loads tail content first.
- Dark log panel: black background with per-level color highlighting.
- Tooltips: Chinese descriptions for key buttons and controls.
- Packaged executable: supports Windows exe packaging via PyInstaller.

## 技术栈 / Tech Stack

- Python 3.10+
- PyQt5
- PyInstaller
- requests
- psutil

## 项目结构 / Project Structure

```text
adb/
├─ adb_tool/
│  ├─ main.py
│  ├─ main_window.py
│  ├─ models/
│  ├─ services/
│  ├─ utils/
│  └─ resources/
├─ requirements.txt
├─ ADB工具管理器.spec
├─ tubiao.ico
├─ PLAN.md
└─ PROJECT_GUIDE.md
```

## 运行 / Run

```powershell
cd adb
pip install -r requirements.txt
python -m adb_tool.main
```

如果本机有多个 Python 环境，请确保运行环境已安装 `PyQt5`、`requests` 和 `psutil`。

If multiple Python environments are installed, make sure the active environment has `PyQt5`, `requests`, and `psutil` installed.

## 打包 / Build

```powershell
cd adb
python -m PyInstaller "ADB工具管理器.spec" --clean --noconfirm
```

打包后的文件默认输出到：

The packaged executable is generated at:

```text
adb/dist/ADB工具管理器.exe
```

## 使用提示 / Usage Notes

- 连接无线设备前，请确认设备已开启 USB 调试或无线调试。
- 如果 `adb connect` 返回连接被拒绝，请检查 IP、端口和设备无线调试状态。
- 如果 ADB daemon 启动失败，请尝试关闭 Android Studio、模拟器或其他占用 ADB 的工具，再重启 ADB 服务。
- Windows 资源管理器可能缓存 exe 图标；如果图标未刷新，可尝试改名或复制到新目录查看。

- Before connecting wirelessly, ensure USB debugging or wireless debugging is enabled on the device.
- If `adb connect` is refused, verify the IP address, port, and wireless debugging status.
- If the ADB daemon fails to start, close Android Studio, emulators, or other tools that may occupy ADB, then restart the ADB server.
- Windows Explorer may cache executable icons. Rename or copy the exe to a new folder if the icon does not refresh.

## License

未指定许可证。发布到 GitHub 前建议补充明确的开源许可证。

No license has been specified. Add an explicit open-source license before publishing publicly.
