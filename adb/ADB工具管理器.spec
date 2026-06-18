# -*- mode: python ; coding: utf-8 -*-

import os

icon_path = os.path.abspath('tubiao.ico')

a = Analysis(
    ['adb_tool\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('adb_tool\\resources\\styles.qss', 'adb_tool\\resources'),
        (icon_path, '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ADB工具管理器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=icon_path,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
