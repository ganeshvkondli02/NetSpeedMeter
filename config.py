
r"""
NetSpeedOverlay Configuration Manager
Stores preferences in %APPDATA%\NetSpeedOverlay\config.json.
"""

import json
import os
from pathlib import Path


class ConfigManager:
    """Manages application settings stored in a JSON file."""

    def __init__(self):
        appdata = os.getenv("APPDATA")

        if appdata:
            self.config_dir = Path(appdata) / "NetSpeedOverlay"
        else:
            self.config_dir = (
                Path.home() / "AppData" / "Roaming" / "NetSpeedOverlay"
            )

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"

        self.defaults = {
            "show_upload": True,
            "show_download": True,
            "show_total": False,
            "update_interval": 1000,
            "font_size": 10,
            "opacity": 0.9,
            "position_x": 20,
            "position_y": 20,
            "always_on_top": True,
            "start_with_windows": False,
            "theme": "dark",
            "unit": "Mbps",
        }

        self.settings = self.load()

    def load(self):
        """Load saved settings and fill in missing defaults."""
        settings = self.defaults.copy()

        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as file:
                    saved = json.load(file)

                if isinstance(saved, dict):
                    settings.update(saved)

            except (OSError, json.JSONDecodeError) as error:
                print(f"Could not load settings: {error}")

        return settings

    def save(self):
        """Save current settings to disk."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            with self.config_file.open("w", encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4)

            return True

        except (OSError, TypeError, ValueError) as error:
            print(f"Could not save settings: {error}")
            return False

    def get(self, key, default=None):
        """Get a setting by name."""
        return self.settings.get(key, default)

    def set(self, key, value, auto_save=True):
        """
        Update one setting.

        auto_save=True saves immediately.
        auto_save=False updates memory; call save() separately.
        """
        self.settings[key] = value

        if auto_save:
            return self.save()

        return True

    def update(self, values, auto_save=True):
        """
        Update multiple settings.

        auto_save=True saves immediately.
        auto_save=False updates memory; call save() separately.
        """
        if not isinstance(values, dict):
            return False

        self.settings.update(values)

        if auto_save:
            return self.save()

        return True

    def reset(self, auto_save=True):
        """Restore default settings."""
        self.settings = self.defaults.copy()

        if auto_save:
            return self.save()

        return True

    def get_all(self):
        """Return a copy of all settings."""
        return self.settings.copy()

    @staticmethod
    def ensure_on_screen(x, y, *args, width=300, height=100):
        """Keep the overlay position within the primary screen."""

        if len(args) >= 1:
            width = args[0]

        if len(args) >= 2:
            height = args[1]

        try:
            from PySide6.QtGui import QGuiApplication

            screen = QGuiApplication.primaryScreen()

            if screen is None:
                return x, y

            area = screen.availableGeometry()

            x = int(x)
            y = int(y)
            width = max(1, int(width))
            height = max(1, int(height))

            max_x = max(area.left(), area.right() - width + 1)
            max_y = max(area.top(), area.bottom() - height + 1)

            x = max(area.left(), min(x, max_x))
            y = max(area.top(), min(y, max_y))

            return x, y

        except (TypeError, ValueError):
            return x, y
