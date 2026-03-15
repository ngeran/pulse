"""
modular_footer.py
─────────────────
Base class for modular footers across all screens.

Provides:
- Global shortcuts (b, m, p, h, q) consistent across all screens
- Extra shortcuts (screen-specific, shown in blue with [x])
- Right content area for time/uptime
- Timer management for auto-updates
"""

from textual.widgets import Static
from textual.containers import Horizontal
from textual.app import ComposeResult
from datetime import datetime
import time
from frontend.ui.widgets.shortcuts_widget import GlobalShortcutsWidget


class ModularFooter(Horizontal):
    """
    Base class for modular footers.

    All screen-specific footers should extend this class.

    Layout:
    [Global Shortcuts + Extra (in blue)] │ [Time/Uptime]
    """

    def __init__(self, extra_shortcuts=None, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.now()
        self._timer = None
        self._extra_shortcuts = extra_shortcuts or []

    def compose(self) -> ComposeResult:
        """Compose the footer with shortcuts and time/uptime."""
        yield GlobalShortcutsWidget(extra_shortcuts=self._extra_shortcuts, id="footer-shortcuts")
        yield Static(id="footer-time")

    def on_mount(self) -> None:
        """Initialize the footer and start updates."""
        self._update_right_content()
        # Update every second
        self._timer = self.set_interval(1, self._update_all)

    def _update_all(self) -> None:
        """Update all footer content."""
        self._update_right_content()

    def _update_right_content(self) -> None:
        """Update the right content area with time and uptime."""
        # Time
        time_str = time.strftime('%H:%M:%S')

        # Uptime
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Combine: time │ uptime
        time_content = f"[#888888]{time_str}[/] │ [#6a8a8a]UP:{uptime_str}[/]"

        try:
            right_widget = self.query_one("#footer-time", Static)
            right_widget.update(time_content)
        except Exception:
            pass

    def set_extra_shortcuts(self, shortcuts: list) -> None:
        """
        Set screen-specific extra shortcuts (shown in blue).

        Args:
            shortcuts: List of (key, description) tuples for screen-specific actions
        """
        try:
            shortcuts_widget = self.query_one("#footer-shortcuts", GlobalShortcutsWidget)
            shortcuts_widget.set_extra_shortcuts(shortcuts)
        except Exception:
            pass

    def start_updates(self, interval: float = 1.0) -> None:
        """Start periodic updates with custom interval."""
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(interval, self._update_all)

    def stop_updates(self) -> None:
        """Stop periodic updates."""
        if self._timer:
            self._timer.stop()
            self._timer = None
