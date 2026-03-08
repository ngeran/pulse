"""
pulse_widgets.py
────────────────
Pulse Dashboard-style widgets.

Provides base widgets with panel-based layouts, progress bars, status badges,
and compact data tables optimized for information density and visual clarity.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


# ──────────────────────────────────────────────────────────────────────────────
# Color Palette
# ──────────────────────────────────────────────────────────────────────────────

PULSE_COLORS: Dict[str, str] = {
    # Status colors (paired with white for readability)
    "critical": "red",
    "warning": "yellow",
    "info": "cyan",
    "success": "green",
    "muted": "grey58",
    "bright": "white",

    # Semantic aliases
    "error": "red",
    "ok": "green",
    "primary": "cyan",
}


# ──────────────────────────────────────────────────────────────────────────────
# Base Panel Widget
# ──────────────────────────────────────────────────────────────────────────────

class PulsePanel(Static):
    """
    Base panel widget with Pulse-style header, body, and footer.

    Features:
    - Collapsible/expandable support
    - Optional header with title and controls
    - Optional footer with summary/stats
    - Consistent border and padding
    """

    DEFAULT_CSS = """
    PulsePanel {
        border: solid $primary;
        padding: 0 1;
        height: 100%;
    }

    .pulse-panel-header {
        text-style: bold;
        background: $primary-darken-1;
        color: $accent;
        border-bottom: solid $primary;
        padding: 0 1;
        height: 1;
    }

    .pulse-panel-body {
        padding: 0 1;
        height: 1fr;
    }

    .pulse-panel-footer {
        text-style: dim;
        color: $text-muted;
        border-top: solid $primary;
        padding: 0 1;
        height: 1;
    }

    .pulse-panel-collapsed {
        height: 3;
    }
    """

    def __init__(
        self,
        title: str = "",
        footer_text: str = "",
        collapsible: bool = False,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._footer_text = footer_text
        self._collapsible = collapsible
        self._collapsed = False

    def compose(self) -> ComposeResult:
        if self._title:
            yield Static(self._title, classes="pulse-panel-header")

        with Vertical(classes="pulse-panel-body"):
            # Subclasses can override this to provide content
            yield Static("")

        if self._footer_text:
            yield Static(self._footer_text, classes="pulse-panel-footer")

    def toggle_collapse(self) -> None:
        """Toggle panel collapse state."""
        if not self._collapsible:
            return
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.add_class("pulse-panel-collapsed")
        else:
            self.remove_class("pulse-panel-collapsed")


# ──────────────────────────────────────────────────────────────────────────────
# Metric Bar (Progress Bar)
# ──────────────────────────────────────────────────────────────────────────────

class MetricBar(Static):
    """
    Horizontal progress bar with color-coded segments and thresholds.

    Displays:
    - Label (e.g., "Health Score")
    - Visual bar with blocks (████████░░░) or percentage
    - Current value with optional percentage
    - Color coding based on thresholds (green/yellow/red)

    Example:
        Health: 85%  ██████░░░░
        Optical: ████░░░░░░ 40%
    """

    DEFAULT_CSS = """
    MetricBar {
        height: 1;
        width: 100%;
    }

    .metric-label {
        color: $text-muted;
        text-style: dim;
    }

    .metric-value {
        text-style: bold;
    }

    .metric-bar-success {
        color: $success;
    }

    .metric-bar-warning {
        color: $warning;
    }

    .metric-bar-critical {
        color: $error;
    }

    .metric-bar-bg {
        color: #666666;
    }
    """

    def __init__(
        self,
        label: str,
        value: float,
        max_value: float = 100,
        show_percentage: bool = True,
        show_label: bool = True,
        compact: bool = False,
        thresholds: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> None:
        """
        Args:
            label: Metric label (e.g., "Health Score")
            value: Current value
            max_value: Maximum value (default 100)
            show_percentage: Show percentage after bar
            show_label: Show label before bar
            compact: Use compact 10-block display (████████░░)
            thresholds: {"warning": 70, "critical": 90} - color thresholds
        """
        super().__init__(**kwargs)
        self._label = label
        self._value = value
        self._max_value = max_value
        self._show_percentage = show_percentage
        self._show_label = show_label
        self._compact = compact
        self._thresholds = thresholds or {"warning": 70, "critical": 90}

    def render(self) -> str:
        percentage = (self._value / self._max_value) * 100 if self._max_value > 0 else 0

        # Determine color based on thresholds
        # For health scores, higher is better (inverted thresholds)
        if percentage < 40:
            color_class = "metric-bar-critical"
            color = "red"
        elif percentage < 70:
            color_class = "metric-bar-warning"
            color = "yellow"
        else:
            color_class = "metric-bar-success"
            color = "green"

        # Build the visual bar
        if self._compact:
            # Compact 10-block display
            filled = int(percentage / 10)
            empty = 10 - filled
            bar = f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
        else:
            # Full width bar with percentage-based blocks
            total_blocks = 20
            filled = int(percentage / 100 * total_blocks)
            empty = total_blocks - filled
            bar = f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"

        # Build label
        label_part = f"{self._label}: " if self._show_label else ""

        # Build percentage suffix
        if self._show_percentage:
            if self._compact:
                # Compact: percentage after bar
                suffix = f" {percentage:.0f}%"
            else:
                # Full: value/max
                suffix = f" {self._value:.0f}/{self._max_value:.0f}"
        else:
            suffix = ""

        return f"{label_part}{bar}{suffix}"

    def update_value(self, value: float) -> None:
        """Update the metric value and refresh display."""
        self._value = value
        self.update(self.render())


# ──────────────────────────────────────────────────────────────────────────────
# Status Badge
# ──────────────────────────────────────────────────────────────────────────────

class StatusBadge(Static):
    """
    Status badge with icon, color, and optional trend indicator.

    Displays:
    - Status icon (● ◌ ◐ ◑ ◒ ◓ ✓ ⚠ ✖)
    - Color-coded based on severity
    - Optional trend arrow (↗ ↘ →)
    - Optional label

    Examples:
        ● Connected (green)
        ⚠ Warning (yellow)
        ✖ Error (red)
        ✓ Score 95 (green) ↗
    """

    DEFAULT_CSS = """
    StatusBadge {
        height: 1;
    }

    .badge-success {
        color: $success;
        text-style: bold;
    }

    .badge-warning {
        color: $warning;
        text-style: bold;
    }

    .badge-critical {
        color: $error;
        text-style: bold;
    }

    .badge-info {
        color: $primary;
        text-style: bold;
    }

    .badge-muted {
        color: $text-muted;
    }

    .trend-improving {
        color: $success;
    }

    .trend-stable {
        color: $primary;
    }

    .trend-degrading {
        color: $warning;
    }

    .trend-critical {
        color: $error;
    }
    """

    # Status icons mapping
    STATUS_ICONS: Dict[str, str] = {
        "connected": "●",
        "connecting": "◌",
        "disconnected": "○",
        "up": "●",
        "down": "○",
        "warning": "⚡",
        "error": "✖",
        "success": "✓",
        "critical": "⚠",
        "info": "ℹ",
        "loading": "◈",
        "unknown": "?",
        "healthy": "●",
        "degraded": "⚡",
        "failed": "✖",
    }

    def __init__(
        self,
        status: str,
        label: str = "",
        trend: Optional[str] = None,
        blink: bool = False,
        **kwargs
    ) -> None:
        """
        Args:
            status: Status type (connected, warning, error, etc.) or custom text
            label: Optional label to display
            trend: Trend direction ("improving", "stable", "degrading", "critical")
            blink: Enable blinking animation
        """
        super().__init__(**kwargs)
        self._status = status.lower()
        self._label = label
        self._trend = trend.lower() if trend else None
        self._blink = blink

    def render(self) -> str:
        # Get icon
        icon = self.STATUS_ICONS.get(self._status, "●")

        # Determine color class
        if self._status in ("connected", "up", "success", "healthy"):
            color_class = "badge-success"
            color = "green"
        elif self._status in ("warning", "degraded", "degrading"):
            color_class = "badge-warning"
            color = "yellow"
        elif self._status in ("error", "down", "critical", "failed"):
            color_class = "badge-critical"
            color = "red"
            if self._blink:
                color_class += " badge-blink"
        elif self._status in ("connecting", "loading"):
            color_class = "badge-info"
            color = "cyan"
        else:
            color_class = "badge-muted"
            color = "grey58"

        # Build trend arrow
        trend_arrow = ""
        if self._trend:
            if self._trend == "improving":
                trend_arrow = " [trend-improving]↗[/trend-improving]"
            elif self._trend == "stable":
                trend_arrow = " [trend-stable]→[/trend-stable]"
            elif self._trend == "degrading":
                trend_arrow = " [trend-degrading]↘[/trend-degrading]"
            elif self._trend == "critical":
                trend_arrow = " [trend-critical]⚠[/trend-critical]"

        # Build label part
        label_part = f" {self._label}" if self._label else ""

        return f"[{color_class}]{icon}[/{color_class}]{label_part}{trend_arrow}"

    def update_status(self, status: str, trend: Optional[str] = None) -> None:
        """Update status and optionally trend."""
        self._status = status.lower()
        if trend is not None:
            self._trend = trend.lower()
        self.update(self.render())


# ──────────────────────────────────────────────────────────────────────────────
# Compact Table
# ──────────────────────────────────────────────────────────────────────────────

class CompactTable(Static):
    """
    Space-optimized table widget with aligned columns.

    Features:
    - Single-line rows with aligned columns
    - Auto-sizing based on content
    - Color-coded cells based on values
    - Scrollbar for large datasets
    - Alternating row colors

    Example:
        ● router1  UP      95%  ✓
        ● router2  UP      78%  ⚡
        ◌ router3  DOWN    --   ✖
    """

    DEFAULT_CSS = """
    CompactTable {
        height: 100%;
    }

    .compact-table-header {
        text-style: bold;
        color: $accent;
        border-bottom: solid $primary;
        padding: 0 1;
    }

    .compact-row-even {
        background: $surface;
    }

    .compact-row-odd {
        background: $surface-darken-1;
    }

    .compact-row-selected {
        background: $primary;
        text-style: bold;
    }

    .compact-cell {
        padding: 0 1;
    }

    .compact-cell-number {
        text-style: bold;
    }
    """

    def __init__(
        self,
        columns: List[str],
        rows: Optional[List[List[str]]] = None,
        column_widths: Optional[List[int]] = None,
        **kwargs
    ) -> None:
        """
        Args:
            columns: List of column headers
            rows: List of rows, each row is a list of cell values
            column_widths: Optional list of column widths (auto if not provided)
        """
        super().__init__(**kwargs)
        self._columns = columns
        self._rows = rows or []
        self._column_widths = column_widths

    def render(self) -> str:
        if not self._columns:
            return ""

        lines = []

        # Calculate column widths if not provided
        if self._column_widths is None:
            self._column_widths = [len(col) for col in self._columns]
            for row in self._rows:
                for i, cell in enumerate(row):
                    if i < len(self._column_widths):
                        self._column_widths[i] = max(
                            self._column_widths[i],
                            len(str(cell))
                        )

        # Render header
        header_parts = []
        for i, (col, width) in enumerate(zip(self._columns, self._column_widths)):
            header_parts.append(f"[bold]{col:<{width}}[/bold]")
        lines.append("  ".join(header_parts))
        lines.append("  " + "─" * (sum(self._column_widths) + len(self._columns) * 2))

        # Render rows
        for row_idx, row in enumerate(self._rows):
            row_class = "compact-row-even" if row_idx % 2 == 0 else "compact-row-odd"
            cell_parts = []
            for i, (cell, width) in enumerate(zip(row, self._column_widths)):
                cell_str = f"[{row_class}]{str(cell):<{width}}[/{row_class}]"
                cell_parts.append(cell_str)
            lines.append("  ".join(cell_parts))

        return "\n".join(lines)

    def add_row(self, row: List[str]) -> None:
        """Add a row to the table."""
        self._rows.append(row)
        self.update(self.render())

    def clear_rows(self) -> None:
        """Clear all rows."""
        self._rows = []
        self.update(self.render())

    def set_rows(self, rows: List[List[str]]) -> None:
        """Set all rows at once."""
        self._rows = rows
        self.update(self.render())


# ──────────────────────────────────────────────────────────────────────────────
# Compact Log Entry
# ──────────────────────────────────────────────────────────────────────────────

class CompactLog(Static):
    """
    Compact activity log with timestamps and color-coded entries.

    Features:
    - Timestamps on all entries (HH:MM:SS format)
    - Single-line format for space efficiency
    - Color-coded by severity
    - Auto-scroll to latest
    - Keeps configurable number of entries

    Example:
        12:34:56 → Connected
        12:34:57 ⚠ WARN: rx power
        12:34:58 ✓ Monitoring started
    """

    DEFAULT_CSS = """
    CompactLog {
        height: 100%;
    }

    .log-timestamp {
        color: $text-muted;
        text-style: dim;
    }

    .log-message {
        width: 1fr;
    }

    .log-entry-info {
        color: $primary;
    }

    .log-entry-success {
        color: $success;
    }

    .log-entry-warning {
        color: $warning;
    }

    .log-entry-error {
        color: $error;
        text-style: bold;
    }

    .log-icon {
        margin: 0 1;
    }
    """

    # Log icons
    LOG_ICONS: Dict[str, str] = {
        "info": "→",
        "success": "✓",
        "warning": "⚠",
        "error": "✖",
    }

    def __init__(
        self,
        max_entries: int = 50,
        show_timestamps: bool = True,
        **kwargs
    ) -> None:
        """
        Args:
            max_entries: Maximum number of entries to keep
            show_timestamps: Show timestamps on entries
        """
        super().__init__(**kwargs)
        self._max_entries = max_entries
        self._show_timestamps = show_timestamps
        self._entries: List[tuple] = []  # (timestamp, message, kind)

    def add_log(self, message: str, kind: str = "info", timestamp: Optional[str] = None) -> None:
        """
        Add a log entry.

        Args:
            message: Log message
            kind: Entry kind (info, success, warning, error)
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")

        self._entries.append((timestamp, message, kind))

        # Trim old entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        self.update(self.render())

    def render(self) -> str:
        lines = []

        for timestamp, message, kind in self._entries:
            icon = self.LOG_ICONS.get(kind, "→")

            if self._show_timestamps:
                lines.append(
                    f"[log-timestamp]{timestamp}[/log-timestamp] "
                    f"[log-entry-{kind}]{icon}[/log-entry-{kind}] "
                    f"{message}"
                )
            else:
                lines.append(
                    f"[log-entry-{kind}]{icon}[/log-entry-{kind}] "
                    f"{message}"
                )

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all log entries."""
        self._entries = []
        self.update(self.render())
