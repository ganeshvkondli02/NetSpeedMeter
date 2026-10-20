# -*- mode: python ; coding: utf-8 -*-

# Keep paths relative to this spec file so the project can be moved
# to another folder or computer without editing this file.
from pathlib import Path

project_dir = str(Path(SPECPATH).resolve())

a = Analysis(
    [str(Path(project_dir) / "main.py")],
    pathex=[project_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        "config",
        "overlay",
        "speed_monitor",
        "tray",
        "settings_dialog",
        "autostart",
    ],
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
    name="NetSpeedOverlay",
    icon=str(Path(project_dir) / "assets" / "app-icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
