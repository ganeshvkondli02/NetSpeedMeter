
r"""
NetSpeedOverlay Windows startup management.
Adds or removes the application from the current user's Startup folder.
"""

import os
import sys
from pathlib import Path


APP_NAME = "NetSpeedOverlay"


def _startup_folder():
    """Return the current user's Windows Startup folder."""
    appdata = os.getenv("APPDATA")

    if not appdata:
        return None

    return (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )


def _startup_file():
    """Return the shortcut/script path used for startup."""
    folder = _startup_folder()

    if folder is None:
        return None

    return folder / f"{APP_NAME}.cmd"


def set_autostart(enabled):
    """
    Enable or disable startup with Windows.

    For a PyInstaller executable, launches the executable directly.
    For a Python script, launches the current Python interpreter
    with the script path.
    """
    startup_file = _startup_file()

    if startup_file is None:
        print("Could not locate the Windows Startup folder.")
        return False

    try:
        startup_file.parent.mkdir(parents=True, exist_ok=True)

        if not enabled:
            if startup_file.exists():
                startup_file.unlink()
            return True

        if getattr(sys, "frozen", False):
            command = f'"{sys.executable}"'
        else:
            script_path = Path(sys.argv[0]).resolve()
            command = f'"{sys.executable}" "{script_path}"'

        content = (
            "@echo off\r\n"
            f"start \"\" {command}\r\n"
        )

        startup_file.write_text(content, encoding="utf-8")
        return True

    except OSError as error:
        print(f"Could not update Windows startup settings: {error}")
        return False


def is_autostart_enabled():
    """Check whether the startup entry exists."""
    startup_file = _startup_file()
    return startup_file is not None and startup_file.exists()
