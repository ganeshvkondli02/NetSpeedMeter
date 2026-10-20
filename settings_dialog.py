
"""
Settings Dialog for NetSpeedOverlay.
Settings are written to ConfigManager only when OK is clicked.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import ConfigManager
import autostart


class SettingsDialog(QDialog):
    """Configuration dialog for NetSpeedOverlay."""

    settings_applied = Signal()

    def __init__(
        self,
        config: ConfigManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.config = config
        self.selected_color = str(
            self.config.get("text_color", "#00FFCC")
        )

        self.setWindowTitle("NetSpeed Overlay Settings")
        self.setWindowFlags(
            (self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(380)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Unit selection
        unit_group = QGroupBox("Network Speed Unit")
        unit_layout = QVBoxLayout(unit_group)

        self.radio_bytes = QRadioButton(
            "Bytes per second (B/s, KB/s, MB/s, GB/s)"
        )
        self.radio_bits = QRadioButton(
            "Bits per second (bps, Kbps, Mbps, Gbps)"
        )

        self.unit_button_group = QButtonGroup(self)
        self.unit_button_group.addButton(self.radio_bytes)
        self.unit_button_group.addButton(self.radio_bits)

        unit_value = str(self.config.get("unit", "bytes")).lower()
        if unit_value in {"bits", "bps", "kbps", "mbps", "gbps"}:
            self.radio_bits.setChecked(True)
        else:
            self.radio_bytes.setChecked(True)

        unit_layout.addWidget(self.radio_bytes)
        unit_layout.addWidget(self.radio_bits)
        layout.addWidget(unit_group)

        # Appearance
        visual_group = QGroupBox("Appearance & Styling")
        visual_layout = QFormLayout(visual_group)
        visual_layout.setSpacing(10)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(9, 32)
        self.spin_font_size.setValue(
            int(self.config.get("font_size", 13))
        )
        visual_layout.addRow("Font Size (pt):", self.spin_font_size)

        color_layout = QHBoxLayout()

        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(50, 26)
        self.btn_color.clicked.connect(self._choose_color)
        self._update_color_button()

        palette_layout = QHBoxLayout()
        palette_layout.setSpacing(4)

        for color in (
            "#00FFCC",
            "#FFFFFF",
            "#00FF66",
            "#FFB703",
            "#38BDF8",
        ):
            chip = QPushButton()
            chip.setFixedSize(20, 20)
            chip.setStyleSheet(
                f"background-color: {color};"
                "border: 1px solid #475569;"
                "border-radius: 3px;"
            )
            chip.setToolTip(f"Set color to {color}")
            chip.clicked.connect(
                lambda checked=False, c=color: self._set_color(c)
            )
            palette_layout.addWidget(chip)

        color_layout.addWidget(self.btn_color)
        color_layout.addLayout(palette_layout)
        color_layout.addStretch()
        visual_layout.addRow("Text Color:", color_layout)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 100)

        opacity = self.config.get(
            "window_opacity",
            self.config.get("opacity", 1.0),
        )
        self.slider_opacity.setValue(
            max(20, min(100, int(float(opacity) * 100)))
        )

        self.lbl_opacity = QLabel(
            f"{self.slider_opacity.value()}%"
        )
        self.slider_opacity.valueChanged.connect(
            lambda value: self.lbl_opacity.setText(f"{value}%")
        )

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.lbl_opacity)
        visual_layout.addRow("Overlay Opacity:", opacity_layout)

        layout.addWidget(visual_group)

        # Behavior
        behavior_group = QGroupBox("Behavior & Startup")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(8)

        self.chk_locked = QCheckBox(
            "Lock Position (prevent accidental dragging)"
        )
        self.chk_locked.setChecked(
            bool(self.config.get("locked", False))
        )
        behavior_layout.addWidget(self.chk_locked)

        self.chk_click_through = QCheckBox(
            "Click-Through Mode (clicks pass to underlying apps)"
        )
        self.chk_click_through.setChecked(
            bool(self.config.get("click_through", False))
        )
        behavior_layout.addWidget(self.chk_click_through)

        self.chk_autostart = QCheckBox(
            "Start automatically with Windows"
        )
        try:
            autostart_enabled = autostart.is_autostart_enabled()
        except Exception:
            autostart_enabled = False

        self.chk_autostart.setChecked(
            autostart_enabled
            or bool(self.config.get("start_with_windows", False))
        )
        behavior_layout.addWidget(self.chk_autostart)

        self.chk_dont_ask = QCheckBox(
            "Don't show this dialog on startup"
        )
        self.chk_dont_ask.setChecked(
            bool(self.config.get("dont_show_startup_dialog", False))
        )
        behavior_layout.addWidget(self.chk_dont_ask)

        layout.addWidget(behavior_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.btn_reset = QPushButton("Reset Defaults")
        self.btn_reset.clicked.connect(self._reset_defaults)
        button_layout.addWidget(self.btn_reset)
        button_layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._save_and_accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)

        layout.addLayout(button_layout)

    def closeEvent(self, event) -> None:
        """Close the settings dialog when the title-bar X is clicked."""
        # Rejecting a QDialog closes it without saving unconfirmed changes.
        self.reject()
        event.accept()

    def _choose_color(self) -> None:
        chosen = QColorDialog.getColor(
            QColor(self.selected_color),
            self,
            "Select Text Color",
        )
        if chosen.isValid():
            self._set_color(chosen.name())

    def _set_color(self, hex_color: str) -> None:
        self.selected_color = hex_color
        self._update_color_button()

    def _update_color_button(self) -> None:
        self.btn_color.setStyleSheet(
            f"background-color: {self.selected_color};"
            "border: 2px solid #334155;"
            "border-radius: 4px;"
        )

    def _reset_defaults(self) -> None:
        """Reset the dialog controls without saving immediately."""
        self.radio_bytes.setChecked(True)
        self.spin_font_size.setValue(13)
        self._set_color("#00FFCC")
        self.slider_opacity.setValue(100)
        self.chk_locked.setChecked(False)
        self.chk_click_through.setChecked(False)
        self.chk_autostart.setChecked(False)
        self.chk_dont_ask.setChecked(False)

    def _save_and_accept(self) -> None:
        """Persist all dialog values, then notify the main application."""
        unit = "bits" if self.radio_bits.isChecked() else "bytes"

        opacity = self.slider_opacity.value() / 100.0

        values = {
            "unit": unit,
            "font_size": self.spin_font_size.value(),
            "text_color": self.selected_color,
            "window_opacity": opacity,
            "opacity": opacity,
            "locked": self.chk_locked.isChecked(),
            "click_through": self.chk_click_through.isChecked(),
            "dont_show_startup_dialog": self.chk_dont_ask.isChecked(),
            "start_with_windows": self.chk_autostart.isChecked(),
        }

        try:
            for key, value in values.items():
                self.config.set(key, value, auto_save=False)

            self.config.save()
            autostart.set_autostart(
                self.chk_autostart.isChecked()
            )
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                self,
                "Settings Error",
                f"Could not save settings:\n{exc}",
            )
            return

        self.settings_applied.emit()
        self.accept()
