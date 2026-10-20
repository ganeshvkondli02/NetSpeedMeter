
"""
NetSpeedOverlay Window
Frameless, transparent, always-on-top network speed HUD.

Features:
- Whole-window dragging
- 0-pixel text padding
- Consistent text outline and spacing
- Position persistence
- Windows topmost refresh to reduce taskbar overlap
- Supports dragging into the Windows taskbar area
- Click-through support
- Right-click context menu
- Multi-monitor positioning
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from config import ConfigManager

WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

PADDING = 0
TEXT_GAP = 3
TEXT_OUTLINE_WIDTH = 2.0


class SpeedOverlayWindow(QWidget):
    """Transparent, frameless, always-on-top network speed HUD."""

    def __init__(
        self,
        config: ConfigManager,
        on_open_settings: Optional[Callable[[], None]] = None,
        on_unit_toggle: Optional[Callable[[], None]] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.config = config
        self.on_open_settings = on_open_settings
        self.on_unit_toggle = on_unit_toggle

        self.down_text = "↓   0.0  MB/s"
        self.up_text = "↑   0.0  MB/s"

        self._dragging = False
        self._drag_start_pos = QPoint()
        self._click_through_enabled = False
        self._context_menu_open = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground, True
        )

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._apply_style()
        self._restore_position()

        # Windows can occasionally place the taskbar above a Qt
        # always-on-top window. Refresh the topmost status periodically
        # without activating the overlay or stealing keyboard focus.
        self._topmost_timer = QTimer(self)
        self._topmost_timer.setInterval(1000)
        self._topmost_timer.timeout.connect(
            self._refresh_topmost
        )

        if sys.platform == "win32":
            self._topmost_timer.start()

    def _get_first(
        self, keys: tuple[str, ...], default
    ):
        """Return the first configured value that is present."""
        for key in keys:
            value = self.config.get(key, None)
            if value is not None:
                return value
        return default

    def _apply_style(self) -> None:
        """Apply font, opacity, dimensions, and mouse settings."""
        font_size = max(
            1, int(self.config.get("font_size", 13))
        )
        font_family = str(
            self.config.get("font_family", "Consolas")
        )

        self.display_font = QFont(
            font_family, font_size, QFont.Weight.Bold
        )
        self.display_font.setStyleHint(
            QFont.StyleHint.Monospace
        )

        opacity = float(
            self._get_first(
                ("window_opacity", "opacity"), 0.9
            )
        )
        self.setWindowOpacity(
            max(0.2, min(1.0, opacity))
        )

        self._update_dimensions()

        self.set_click_through(
            bool(self.config.get("click_through", False))
        )
        self.update()

    def _update_dimensions(self) -> None:
        """Calculate the window size while keeping text padding at zero."""
        fm = QFontMetrics(self.display_font)

        text_width = max(
            fm.horizontalAdvance(self.down_text),
            fm.horizontalAdvance(self.up_text),
        )

        outline_allowance = int(
            TEXT_OUTLINE_WIDTH + 1
        )

        self.overlay_width = (
            text_width + 2 * outline_allowance
        )
        self.overlay_height = (
            2 * fm.height()
            + TEXT_GAP
            + 2 * outline_allowance
        )

        self.setFixedSize(
            self.overlay_width,
            self.overlay_height,
        )

    def _restore_position(self) -> None:
        """Restore the saved position within a physical display."""
        saved_x = self._get_first(
            ("position_x", "pos_x"), -1
        )
        saved_y = self._get_first(
            ("position_y", "pos_y"), -1
        )

        try:
            saved_x = int(saved_x)
            saved_y = int(saved_y)
        except (TypeError, ValueError):
            saved_x = saved_y = -1

        screen = QApplication.primaryScreen()

        if screen is None:
            self.move(20, 20)
            return

        if saved_x < 0 or saved_y < 0:
            geometry = screen.geometry()
            x = geometry.right() - self.width() + 1 - 24
            y = geometry.top() + 24
        else:
            x, y = saved_x, saved_y

        x, y = self._clamp_position(x, y)
        self.move(x, y)

    def _screen_for_position(self, x: int, y: int):
        """Choose the display containing the proposed window position."""
        screens = QApplication.screens()

        if not screens:
            return None

        point = QPoint(int(x), int(y))

        for screen in screens:
            if screen.geometry().contains(point):
                return screen

        return QApplication.primaryScreen()

    def _clamp_position(
        self, x: int, y: int
    ) -> tuple[int, int]:
        """Keep the overlay inside the physical screen geometry."""
        screen = self._screen_for_position(x, y)

        if screen is None:
            return int(x), int(y)

        area = screen.geometry()

        max_x = max(
            area.left(),
            area.right() - self.width() + 1,
        )
        max_y = max(
            area.top(),
            area.bottom() - self.height() + 1,
        )

        x = max(area.left(), min(int(x), max_x))
        y = max(area.top(), min(int(y), max_y))

        return x, y

    def _save_position(self) -> None:
        """Persist the current overlay coordinates."""
        x, y = self.x(), self.y()

        if hasattr(self.config, "save_position"):
            try:
                self.config.save_position(x, y)
                return
            except (TypeError, AttributeError):
                pass

        self.config.set(
            "position_x", x, auto_save=False
        )
        self.config.set(
            "position_y", y, auto_save=False
        )
        self.config.save()

    def _refresh_topmost(self) -> None:
        """
        Reassert Windows topmost status without moving the window
        or activating it.

        Do not run this while the context menu is open, so the menu
        remains usable and is not repeatedly covered.
        """
        if (
            sys.platform != "win32"
            or not self.isVisible()
            or self._context_menu_open
        ):
            return

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            user32.SetWindowPos.argtypes = [
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL

            hwnd = wintypes.HWND(int(self.winId()))
            HWND_TOPMOST = wintypes.HWND(-1)

            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOACTIVATE = 0x0010
            SWP_NOOWNERZORDER = 0x0200

            flags = (
                SWP_NOSIZE
                | SWP_NOMOVE
                | SWP_NOACTIVATE
                | SWP_NOOWNERZORDER
            )

            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                flags,
            )

        except Exception as exc:
            print(
                f"[Overlay] Topmost refresh failed: {exc}"
            )

    def showEvent(self, event) -> None:
        """Reassert topmost status when the overlay becomes visible."""
        super().showEvent(event)

        if sys.platform == "win32":
            QTimer.singleShot(100, self._refresh_topmost)

    def set_click_through(self, enabled: bool) -> None:
        """Enable or disable mouse transparency."""
        enabled = bool(enabled)
        self._click_through_enabled = enabled

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            enabled,
        )

        if sys.platform == "win32":
            try:
                import ctypes

                hwnd = int(self.winId())
                user32 = ctypes.windll.user32

                current_style = user32.GetWindowLongW(
                    hwnd, -20
                )

                if enabled:
                    new_style = (
                        current_style
                        | WS_EX_TRANSPARENT
                        | WS_EX_LAYERED
                    )
                else:
                    new_style = (
                        current_style & ~WS_EX_TRANSPARENT
                    )

                user32.SetWindowLongW(
                    hwnd, -20, new_style
                )

            except Exception as exc:
                print(
                    f"[Overlay] Click-through update failed: {exc}"
                )

    def update_speed(
        self, down_str: str, up_str: str
    ) -> None:
        """Update speed labels and resize when necessary."""
        if (
            down_str == self.down_text
            and up_str == self.up_text
        ):
            return

        old_x, old_y = self.x(), self.y()

        self.down_text = down_str
        self.up_text = up_str

        self._update_dimensions()

        x, y = self._clamp_position(old_x, old_y)
        self.move(x, y)
        self.update()

    def reload_config(self) -> None:
        """Apply changed settings and preserve the current position."""
        old_x, old_y = self.x(), self.y()

        self._apply_style()

        x, y = self._clamp_position(old_x, old_y)
        self.move(x, y)

        if sys.platform == "win32":
            QTimer.singleShot(100, self._refresh_topmost)

    def paintEvent(self, event) -> None:
        """Draw the background and both speed lines."""
        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing, True
        )
        painter.setRenderHint(
            QPainter.RenderHint.TextAntialiasing, True
        )

        bg_opacity = float(
            self.config.get("bg_opacity", 0.0)
        )

        if bg_opacity > 0.01:
            alpha = int(
                max(0.0, min(1.0, bg_opacity)) * 255
            )

            painter.setBrush(
                QColor(10, 15, 26, alpha)
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(
                self.rect(), 0, 0
            )

        painter.setFont(self.display_font)

        fm = QFontMetrics(self.display_font)
        ascent = fm.ascent()
        line_height = fm.height()

        outline_allowance = int(
            TEXT_OUTLINE_WIDTH + 1
        )

        x_text = outline_allowance
        y1 = outline_allowance + ascent
        y2 = y1 + line_height + TEXT_GAP

        color_hex = str(
            self.config.get("text_color", "#00FFCC")
        )

        primary_color = QColor(color_hex)
        shadow_color = QColor(0, 0, 0, 230)
        outline_color = QColor(0, 0, 0, 210)

        for text, baseline_y in (
            (self.down_text, y1),
            (self.up_text, y2),
        ):
            path = QPainterPath()
            path.addText(
                x_text,
                baseline_y,
                self.display_font,
                text,
            )

            painter.save()
            painter.translate(1, 1)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow_color)
            painter.drawPath(path)
            painter.restore()

            painter.setPen(
                QPen(
                    outline_color,
                    TEXT_OUTLINE_WIDTH,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(primary_color)
            painter.drawPath(path)

        painter.end()

    def mousePressEvent(
        self, event: QMouseEvent
    ) -> None:
        """Start dragging from anywhere inside the overlay."""
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(
                event.globalPosition().toPoint()
            )
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if not bool(
                self.config.get("locked", False)
            ):
                self._dragging = True
                self._drag_start_pos = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(
        self, event: QMouseEvent
    ) -> None:
        """Move the overlay, including over the taskbar area."""
        if (
            self._dragging
            and not bool(
                self.config.get("locked", False)
            )
        ):
            global_pos = event.globalPosition().toPoint()
            new_pos = global_pos - self._drag_start_pos

            x, y = self._clamp_position(
                new_pos.x(), new_pos.y()
            )

            self.move(x, y)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(
        self, event: QMouseEvent
    ) -> None:
        """Save the final position after dragging."""
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._dragging
        ):
            self._dragging = False

            x, y = self._clamp_position(
                self.x(), self.y()
            )

            self.move(x, y)
            self._save_position()

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _show_context_menu(
        self, global_pos: QPoint
    ) -> None:
        """Display the right-click context menu."""
        menu = QMenu(self)

        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
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

        current_unit = str(
            self.config.get("unit", "bytes")
        ).strip().lower()

        is_bits = current_unit in {
            "bit", "bits", "bps",
            "kbps", "mbps", "gbps",
        }

        action_unit = menu.addAction(
            "Switch to Bytes (MB/s)"
            if is_bits
            else "Switch to Bits (Mbps)"
        )

        action_settings = menu.addAction("Settings...")
        menu.addSeparator()

        is_locked = bool(
            self.config.get("locked", False)
        )

        action_lock = menu.addAction(
            "Unlock Position"
            if is_locked
            else "Lock Position"
        )

        click_through = bool(
            self.config.get("click_through", False)
        )

        action_click_through = menu.addAction(
            "Disable Click-Through"
            if click_through
            else "Enable Click-Through"
        )

        action_reset_pos = menu.addAction(
            "Reset Position (Top-Right)"
        )

        menu.addSeparator()

        action_hide = menu.addAction("Hide Overlay")
        action_quit = menu.addAction("Quit")

        self._context_menu_open = True

        try:
            selected = menu.exec(global_pos)
        finally:
            self._context_menu_open = False

        if selected == action_unit:
            # main.py is the sole owner of the unit change.
            # Do not update config here, or the unit may toggle twice.
            if self.on_unit_toggle:
                self.on_unit_toggle()

        elif selected == action_settings:
            if self.on_open_settings:
                self.on_open_settings()

        elif selected == action_lock:
            self.config.set("locked", not is_locked)

        elif selected == action_click_through:
            new_value = not click_through
            self.config.set("click_through", new_value)
            self.set_click_through(new_value)

        elif selected == action_reset_pos:
            screen = QApplication.primaryScreen()

            if screen is not None:
                geometry = screen.geometry()

                x = (
                    geometry.right()
                    - self.width()
                    + 1
                    - 24
                )
                y = geometry.top() + 24

                x, y = self._clamp_position(x, y)
                self.move(x, y)
                self._save_position()

        elif selected == action_hide:
            self.hide()

        elif selected == action_quit:
            QApplication.quit()
