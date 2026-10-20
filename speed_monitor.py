
"""
Network Speed Monitor with EMA Smoothing.

Samples network throughput via psutil every 1 second and calculates
download and upload rates using exponential smoothing.

Internal rates are always measured in bytes per second.
Bytes mode displays B/s, KB/s, MB/s, GB/s using base 1024.
Bits mode displays bps, Kbps, Mbps, Gbps using base 1000.
"""

from __future__ import annotations

import math
import time

import psutil
from PySide6.QtCore import QObject, QTimer, Signal, Qt


DEFAULT_SMOOTHING_WINDOW_SECONDS: float = 0.35


def normalize_unit_mode(unit_mode: str) -> str:
    """
    Normalize unit names to 'bits' or 'bytes'.

    Lowercase b means bits; uppercase B means bytes.
    Full names and common display units are also accepted.
    """
    if unit_mode is None:
        return "bytes"

    # Preserve case because b and B have different meanings.
    value = str(unit_mode).strip()

    if value in {"b", "bit", "bits", "bps", "Kbps", "Mbps", "Gbps",
                 "kbps", "mbps", "gbps"}:
        return "bits"

    if value in {"B", "byte", "bytes", "B/s", "KB/s", "MB/s", "GB/s",
                 "kB/s", "MBps", "GBps"}:
        return "bytes"

    # Accommodate common saved setting values.
    lowered = value.lower()

    if lowered in {"bits", "bit", "bps"}:
        return "bits"

    if lowered in {"bytes", "byte", "b/s"}:
        return "bytes"

    # Default to bytes to preserve the app's existing default.
    return "bytes"


def format_speed(
    bytes_per_sec: float,
    unit_mode: str = "bytes",
) -> str:
    """
    Format speed from a bytes-per-second value.

    Bits mode: bps, Kbps, Mbps, Gbps (base 1000).
    Bytes mode: B/s, KB/s, MB/s, GB/s (base 1024).
    """
    rate = max(0.0, float(bytes_per_sec))
    mode = normalize_unit_mode(unit_mode)

    if mode == "bits":
        bits_per_sec = rate * 8.0

        if bits_per_sec < 1_000:
            return f"{bits_per_sec:>5.0f}  bps"
        if bits_per_sec < 1_000_000:
            return f"{bits_per_sec / 1_000:>5.1f} Kbps"
        if bits_per_sec < 1_000_000_000:
            return f"{bits_per_sec / 1_000_000:>5.1f} Mbps"

        return f"{bits_per_sec / 1_000_000_000:>5.2f} Gbps"

    if rate < 1024:
        return f"{rate:>5.0f}   B/s"
    if rate < 1024**2:
        return f"{rate / 1024:>5.1f}  KB/s"
    if rate < 1024**3:
        return f"{rate / (1024**2):>5.1f}  MB/s"

    return f"{rate / (1024**3):>5.2f}  GB/s"


class SpeedMonitor(QObject):
    """Samples network traffic and smooths rates using an EMA."""

    # down_text, up_text, download bytes/sec, upload bytes/sec
    speed_updated = Signal(str, str, float, float)

    def __init__(
        self,
        sample_interval_ms: int = 1000,
        smoothing_window_s: float = DEFAULT_SMOOTHING_WINDOW_SECONDS,
        unit_mode: str = "bytes",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.sample_interval_ms = max(100, int(sample_interval_ms))
        self.smoothing_window_s = max(0.05, float(smoothing_window_s))
        self.unit_mode = normalize_unit_mode(unit_mode)

        counters = psutil.net_io_counters()
        self._last_bytes_recv = counters.bytes_recv
        self._last_bytes_sent = counters.bytes_sent
        self._last_time = time.perf_counter()

        self._smoothed_down_bps = 0.0
        self._smoothed_up_bps = 0.0

        self._last_down_str = ""
        self._last_up_str = ""

        self._timer = QTimer(self)
        self._timer.setInterval(self.sample_interval_ms)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._sample)

    def start(self) -> None:
        """Start monitoring network traffic."""
        counters = psutil.net_io_counters()
        self._last_bytes_recv = counters.bytes_recv
        self._last_bytes_sent = counters.bytes_sent
        self._last_time = time.perf_counter()
        self._timer.start()

    def stop(self) -> None:
        """Stop monitoring network traffic."""
        self._timer.stop()

    def set_unit_mode(self, mode: str) -> None:
        """Change display units and refresh the display."""
        self.unit_mode = normalize_unit_mode(mode)
        self._last_down_str = ""
        self._last_up_str = ""
        self._emit_current_rates()

    def set_smoothing_window(self, seconds: float) -> None:
        """Change the EMA smoothing window."""
        self.smoothing_window_s = max(0.05, float(seconds))

    def _emit_current_rates(self) -> None:
        """Format and emit the most recent smoothed rates."""
        down_text = (
            f"↓ {format_speed(self._smoothed_down_bps, self.unit_mode)}"
        )
        up_text = (
            f"↑ {format_speed(self._smoothed_up_bps, self.unit_mode)}"
        )

        self._last_down_str = down_text
        self._last_up_str = up_text

        self.speed_updated.emit(
            down_text,
            up_text,
            self._smoothed_down_bps,
            self._smoothed_up_bps,
        )

    def _sample(self) -> None:
        """Read network counters and calculate smoothed rates."""
        now = time.perf_counter()
        dt = now - self._last_time

        if dt <= 0:
            return

        try:
            counters = psutil.net_io_counters()
        except Exception as error:
            print(f"[SpeedMonitor] Could not read counters: {error}")
            return

        delta_recv = max(
            0, counters.bytes_recv - self._last_bytes_recv
        )
        delta_sent = max(
            0, counters.bytes_sent - self._last_bytes_sent
        )

        self._last_bytes_recv = counters.bytes_recv
        self._last_bytes_sent = counters.bytes_sent
        self._last_time = now

        raw_down = delta_recv / dt
        raw_up = delta_sent / dt

        alpha = 1.0 - math.exp(
            -dt / self.smoothing_window_s
        )

        self._smoothed_down_bps = (
            alpha * raw_down
            + (1.0 - alpha) * self._smoothed_down_bps
        )
        self._smoothed_up_bps = (
            alpha * raw_up
            + (1.0 - alpha) * self._smoothed_up_bps
        )

        if self._smoothed_down_bps < 1.0:
            self._smoothed_down_bps = 0.0

        if self._smoothed_up_bps < 1.0:
            self._smoothed_up_bps = 0.0

        down_text = (
            f"↓ {format_speed(self._smoothed_down_bps, self.unit_mode)}"
        )
        up_text = (
            f"↑ {format_speed(self._smoothed_up_bps, self.unit_mode)}"
        )

        if (
            down_text != self._last_down_str
            or up_text != self._last_up_str
        ):
            self._last_down_str = down_text
            self._last_up_str = up_text

            self.speed_updated.emit(
                down_text,
                up_text,
                self._smoothed_down_bps,
                self._smoothed_up_bps,
            )
