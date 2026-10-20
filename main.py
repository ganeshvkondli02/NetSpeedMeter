
"""
NetSpeedOverlay - Windows Desktop Live Network Speed HUD.
Coordinates the overlay, speed monitor, settings, and system tray.
"""

from __future__ import annotations

import os
import sys

# Set Qt scaling options before importing PySide6.
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from config import ConfigManager
from overlay import SpeedOverlayWindow
from settings_dialog import SettingsDialog
from speed_monitor import SpeedMonitor, normalize_unit_mode
from tray import TrayManager


def normalize_unit(value: object) -> str:
    """Normalize stored unit preferences to 'bits' or 'bytes'."""
    return normalize_unit_mode(str(value))


class NetSpeedApp:
    """Coordinates the overlay, speed monitor, settings, and tray."""

    def __init__(self) -> None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        self.app = QApplication(sys.argv)
        self.app.setApplicationName("NetSpeedOverlay")
        self.app.setOrganizationName("NetSpeedStudio")
        self.app.setQuitOnLastWindowClosed(False)

        # Keep the Windows named-mutex handle alive for the lifetime of
        # this application. A second launch exits before creating a UI.
        # If mutex setup fails, continue launching rather than hiding the app.
        self._single_instance_mutex = None
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CreateMutexW.argtypes = (
                    wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR
                )
                kernel32.CreateMutexW.restype = wintypes.HANDLE
                mutex = kernel32.CreateMutexW(
                    None, False, "Local\\NetSpeedOverlay_SingleInstance_Mutex"
                )
                if mutex:
                    ERROR_ALREADY_EXISTS = 183
                    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                        kernel32.CloseHandle(mutex)
                        raise SystemExit(0)
                    self._single_instance_mutex = (kernel32, mutex)
            except SystemExit:
                raise
            except Exception:
                # Do not prevent the app from starting if lock setup fails.
                self._single_instance_mutex = None

        self.config = ConfigManager()

        smoothing_ms = self.config.get(
            "smoothing_window_ms", 350
        )

        try:
            smoothing_seconds = (
                max(50, int(smoothing_ms)) / 1000.0
            )
        except (TypeError, ValueError):
            smoothing_seconds = 0.35

        unit = normalize_unit(
            self.config.get("unit", "bytes")
        )
        self.config.set("unit", unit, auto_save=False)

        self.monitor = SpeedMonitor(
            sample_interval_ms=1000,
            smoothing_window_s=smoothing_seconds,
            unit_mode=unit,
        )

        self.overlay = SpeedOverlayWindow(
            config=self.config,
            on_open_settings=self.open_settings,
            on_unit_toggle=self.toggle_unit,
        )

        # The monitor emits new formatted strings whenever units change.
        self.monitor.speed_updated.connect(
            self.overlay.update_speed
        )

        self.tray = TrayManager(
            config=self.config,
            overlay_window=self.overlay,
            on_open_settings=self.open_settings,
            on_unit_toggle=self.toggle_unit,
        )
        self.tray.show()

        self._settings_dialog: SettingsDialog | None = None

    def toggle_unit(self) -> None:
        """
        Toggle units exactly once and synchronize the application.

        Some UI callbacks may already update the config before calling
        this method. Compare the saved preference with the monitor's
        actual mode to avoid accidentally toggling back.
        """
        configured_unit = normalize_unit(
            self.config.get("unit", "bytes")
        )

        monitor_unit = normalize_unit(
            self.monitor.unit_mode
        )

        if configured_unit != monitor_unit:
            # A caller already selected the new mode.
            new_unit = configured_unit
        else:
            # No caller changed the setting; toggle it here.
            new_unit = (
                "bits"
                if monitor_unit == "bytes"
                else "bytes"
            )

        # Save the final setting.
        self.config.set("unit", new_unit)

        # Update the monitor. set_unit_mode emits the current speeds
        # immediately, so the overlay can refresh without waiting
        # for the next one-second sampling interval.
        self.monitor.set_unit_mode(new_unit)

        # Refresh tray labels or checked states.
        self.tray.sync_state()

    def open_settings(self) -> None:
        """Open or focus the settings dialog."""
        if (
            self._settings_dialog is not None
            and self._settings_dialog.isVisible()
        ):
            self._settings_dialog.activateWindow()
            self._settings_dialog.raise_()
            return

        dialog = SettingsDialog(self.config)
        self._settings_dialog = dialog

        dialog.settings_applied.connect(
            self._on_settings_applied
        )

        try:
            dialog.exec()
        finally:
            self._settings_dialog = None

    def _on_settings_applied(self) -> None:
        """Apply saved settings to the monitor, overlay, and tray."""
        unit = normalize_unit(
            self.config.get("unit", "bytes")
        )

        self.config.set("unit", unit)
        self.monitor.set_unit_mode(unit)

        self.overlay.reload_config()
        self.tray.sync_state()

    def run(self) -> int:
        """Show startup settings if enabled, then start monitoring."""
        if not bool(
            self.config.get("dont_show_startup_dialog", False)
        ):
            dialog = SettingsDialog(self.config)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                self._on_settings_applied()

        self.overlay.show()
        self.monitor.start()

        return self.app.exec()


def main() -> None:
    application = NetSpeedApp()
    sys.exit(application.run())


if __name__ == "__main__":
    main()
