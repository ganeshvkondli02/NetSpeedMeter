"""
System Tray Integration for NetSpeedOverlay
Provides a taskbar notification area icon with quick actions and toggle support.
"""

from __future__ import annotations
from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from config import ConfigManager


def create_default_tray_icon() -> QIcon:
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.setBrush(QColor(15, 23, 42))
    painter.setPen(QColor(51, 65, 85))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 12, 12)

    painter.setFont(QFont("Arial", 22, QFont.Weight.Bold))
    painter.setPen(QColor(0, 255, 204))
    painter.drawText(8, 40, "↓")

    painter.setPen(QColor(56, 189, 248))
    painter.drawText(34, 40, "↑")

    painter.end()
    return QIcon(pixmap)


class TrayManager:
    def __init__(
        self,
        config: ConfigManager,
        overlay_window,
        on_open_settings: Callable[[], None],
        on_unit_toggle: Callable[[], None],
    ) -> None:
        self.config = config
        self.overlay = overlay_window
        self.on_open_settings = on_open_settings
        self.on_unit_toggle = on_unit_toggle

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(create_default_tray_icon())
        self.tray.setToolTip("NetSpeed Overlay - Live Network Speed Monitor")

        self._build_menu()
        self.tray.activated.connect(self._on_tray_activated)

    def show(self) -> None:
        self.tray.show()

    def _build_menu(self) -> None:
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                padding: 4px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 22px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #38bdf8;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 6px;
            }
        """)

        self.action_toggle_visible = QAction("Hide Overlay", self.menu)
        self.action_toggle_visible.triggered.connect(self._toggle_overlay_visibility)
        self.menu.addAction(self.action_toggle_visible)

        is_ct = bool(self.config.get("click_through", False))
        self.action_click_through = QAction("Disable Click-Through" if is_ct else "Enable Click-Through", self.menu)
        self.action_click_through.triggered.connect(self._toggle_click_through)
        self.menu.addAction(self.action_click_through)

        current_unit = self.config.get("unit", "bytes")
        unit_label = "Switch to Bits (Mbps)" if current_unit == "bytes" else "Switch to Bytes (MB/s)"
        self.action_unit = QAction(unit_label, self.menu)
        self.action_unit.triggered.connect(self._on_unit_action)
        self.menu.addAction(self.action_unit)

        self.menu.addSeparator()

        action_settings = QAction("Settings...", self.menu)
        action_settings.triggered.connect(self.on_open_settings)
        self.menu.addAction(action_settings)

        self.menu.addSeparator()

        action_quit = QAction("Quit NetSpeed Overlay", self.menu)
        action_quit.triggered.connect(QApplication.quit)
        self.menu.addAction(action_quit)

        self.tray.setContextMenu(self.menu)

    def _toggle_overlay_visibility(self) -> None:
        if self.overlay.isVisible():
            self.overlay.hide()
            self.action_toggle_visible.setText("Show Overlay")
        else:
            self.overlay.show()
            self.action_toggle_visible.setText("Hide Overlay")

    def _toggle_click_through(self) -> None:
        current = bool(self.config.get("click_through", False))
        new_state = not current
        self.config.set("click_through", new_state)
        self.overlay.set_click_through(new_state)
        self.action_click_through.setText("Disable Click-Through" if new_state else "Enable Click-Through")

    def _on_unit_action(self) -> None:
        current_unit = self.config.get("unit", "bytes")
        new_unit = "bits" if current_unit == "bytes" else "bytes"
        self.config.set("unit", new_unit)
        self.on_unit_toggle()
        self.action_unit.setText("Switch to Bits (Mbps)" if new_unit == "bytes" else "Switch to Bytes (MB/s)")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_overlay_visibility()

    def sync_state(self) -> None:
        if self.overlay.isVisible():
            self.action_toggle_visible.setText("Hide Overlay")
        else:
            self.action_toggle_visible.setText("Show Overlay")

        is_ct = bool(self.config.get("click_through", False))
        self.action_click_through.setText("Disable Click-Through" if is_ct else "Enable Click-Through")

        unit = self.config.get("unit", "bytes")
        self.action_unit.setText("Switch to Bits (Mbps)" if unit == "bytes" else "Switch to Bytes (MB/s)")
