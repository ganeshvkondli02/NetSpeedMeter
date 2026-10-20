<<<<<<< HEAD
# NetSpeedOverlay

A lightweight, frameless, always-on-top live network speed overlay for Windows built with **Python 3.11+**, **PySide6**, and **psutil**.

---

## ⚡ Core Features

- **HUD Overlay Window**:
  - Frameless, translucent background with zero window chrome.
  - Always-on-top (`Qt.WindowStaysOnTopHint`), visible over borderless/windowed-fullscreen games, browsers, and streaming videos.
  - Excluded from the Windows taskbar and Alt+Tab (`Qt.WindowType.Tool`).
  - Outlined typography with drop shadow for 100% legibility over any background.
- **High-Resolution Speed Engine**:
  - 10 ms sampling interval using hardware high-resolution timers (`PreciseTimer`).
  - Speed computed from real elapsed time (`time.perf_counter()`), not assumed timer intervals.
  - **Exponential Moving Average (EMA)** smoothing window (~200–500 ms) eliminates 10 ms jitter while staying responsive to bandwidth spikes.
  - Fixed-width monospace typography (`Consolas`) prevents horizontal text jitter.
  - Auto-scaling units:
    - **Bytes mode**: `B/s`, `KB/s`, `MB/s`, `GB/s` (base 1024)
    - **Bits mode**: `bps`, `Kbps`, `Mbps`, `Gbps` (base 1000 telecom standard)
- **Position Persistence**:
  - Left-click drag anywhere on the overlay to reposition.
  - Coordinates saved to `%APPDATA%\NetSpeedOverlay\config.json`.
  - Multi-monitor boundary safety clamping guarantees the overlay never restores off-screen.
- **Click-Through Mode**:
  - Transparent to mouse clicks (`WS_EX_TRANSPARENT | WS_EX_LAYERED`). Clicks pass directly to games or underlying desktop applications.
  - Can be toggled on/off at any time via the System Tray icon or context menu.
- **Startup Settings & System Tray**:
  - Optional settings modal on first startup with "Don't ask again" option.
  - System Tray icon with quick actions: Show/Hide, Switch Units, Click-Through Toggle, Settings, Lock Position, and Quit.
  - Optional "Start with Windows" registry integration (`HKCU\...\Run`).
- **Performance**:
  - Target CPU utilization < 1-2%.
  - Conditional repainting: redraws only occur when the formatted text changes.
  - Safe network adapter rollover and reconnect handling (negative deltas clamped to 0).

---

## 📦 Requirements

- **Windows 10 / 11** (64-bit recommended)
- **Python 3.11+**
- Dependencies: `pyside6>=6.6.0`, `psutil>=5.9.0`, `pyinstaller>=6.3.0`

---

## 🚀 Quick Start (Development)

```cmd
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 🔨 Packaging as a Standalone .exe (PyInstaller)

On Windows, double-click `build.bat`. It installs the dependencies, clears old
`build/` and `dist/` outputs, and builds using `NetSpeedOverlay.spec`.

You can also run these commands from the project folder:

```cmd
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean NetSpeedOverlay.spec
```

Executable output: `dist\\NetSpeedOverlay.exe`. The spec file uses paths
relative to itself, so the project can be moved without editing an absolute path.

---

## ⚠️ Known Limitations

1. **Exclusive Fullscreen Mode**:
   - The overlay relies on the Windows Desktop Window Manager (DWM). Games running in hardware *Exclusive Fullscreen* mode bypass the DWM compositor.
   - **Solution**: Set your game display mode to **Borderless Fullscreen** or **Windowed Fullscreen**.
2. **Elevated (Administrator) Windows**:
   - Under Windows UIPI, a standard user process cannot overlay an elevated Administrator window.
   - **Solution**: Launch `NetSpeedOverlay.exe` with Administrator privileges if needed.


### Single-instance behavior

Only one NetSpeedOverlay process is allowed to run at a time. If you launch the EXE again while it is already running, the extra launch exits without opening another copy.
=======
# NetSpeedMeter
A lightweight Windows internet speed overlay built with Python
>>>>>>> 266887aa7d9f89b7ec07d489191fe1942baa7b82
