"""
footer_modules.py
─────────────────
Modular footer components for building custom footers.

Each module is a self-contained widget that can be added to a footer.
Modules include shortcuts, status indicators, info widgets, etc.
"""

from textual.widgets import Static
from textual.containers import Horizontal
from textual.app import ComposeResult
from typing import Optional, List
import time
from datetime import datetime


class FooterModule(Static):
    """
    Base class for footer modules.

    All footer modules should inherit from this class.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_timer = None

    def start_updates(self, interval: float = 1.0) -> None:
        """Start periodic updates for this module."""
        if self._update_timer is None:
            self._update_timer = self.set_interval(interval, self._update)

    def stop_updates(self) -> None:
        """Stop periodic updates for this module."""
        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None

    def _update(self) -> None:
        """Update method called periodically. Override in subclasses."""
        pass


class ShortcutsModule(FooterModule):
    """
    Module displaying keyboard shortcuts.

    Shortcuts are displayed as [key] description format.
    """

    def __init__(self, shortcuts: Optional[List[tuple]] = None, **kwargs):
        super().__init__(**kwargs)
        self.shortcuts = shortcuts or []

    def set_shortcuts(self, shortcuts: List[tuple]) -> None:
        """Set the shortcuts to display.

        Args:
            shortcuts: List of (key, description) tuples
                      Example: [('c', 'Connect'), ('d', 'Disconnect')]
        """
        self.shortcuts = shortcuts
        self._update_content()

    def add_shortcut(self, key: str, description: str) -> None:
        """Add a single shortcut."""
        self.shortcuts.append((key, description))
        self._update_content()

    def _update_content(self) -> None:
        """Update the shortcuts display."""
        if not self.shortcuts:
            self.update("")
            return

        parts = []
        for key, desc in self.shortcuts:
            # Format: [key] desc
            parts.append(f"[{key}] {desc}")

        # Join with separator
        separator = " │ "
        content = separator.join(parts)

        self.update(content)


class StatusModule(FooterModule):
    """
    Module displaying status indicators.

    Shows colored status badges for various system states.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ws_status = "OFFLINE"
        self._api_status = "INACTIVE"
        self._polling_status = "OFF"
        self._selected_devices = 0
        self._mounted = False  # Track if mounted

    def on_mount(self) -> None:
        """Initialize and start updates."""
        self._mounted = True
        self._update_content()
        self.start_updates(1.0)

    def _update(self) -> None:
        """Update status indicators."""
        # Only update if mounted and part of a live app
        if not self._mounted or not self.is_mounted:
            return
        self._update_from_app()
        self._update_content()

    def _update_from_app(self) -> None:
        """Update status values from app state."""
        try:
            app = self.app

            # WebSocket status
            ws_online = hasattr(app, 'ws_connected') and app.ws_connected
            self._ws_status = "ONLINE" if ws_online else "OFFLINE"

            # API status
            if hasattr(app, 'conn_mgr') and app.conn_mgr:
                sessions = app.conn_mgr.sessions
                connected = sum(
                    1 for session in sessions.values()
                    if hasattr(session, 'state') and session.state.value == "CONNECTED"
                )
                self._api_status = "ACTIVE" if connected > 0 else "INACTIVE"
        except Exception:
            pass

    def _update_content(self) -> None:
        """Update the status indicators."""
        parts = []

        # WebSocket status
        if self._ws_status == "ONLINE":
            parts.append("[#5aba5a on #2a4a2a]WS[/]")
        else:
            parts.append("[#ba5a5a on #4a2a2a]WS[/]")

        # API status
        if self._api_status == "ACTIVE":
            parts.append("[#5aba5a on #2a4a2a]API[/]")
        else:
            parts.append("[#ba8a5a on #4a3a2a]API[/]")

        # Polling status
        if self._polling_status == "ON":
            parts.append("[#5aba5a on #2a4a2a]POLL[/]")
        else:
            parts.append("[#888888 on #3a3a3a]POLL[/]")

        # Device selection
        if self._selected_devices > 0:
            parts.append(f"[#00d7ff]SEL:{self._selected_devices}[/]")

        # Join with separator
        if parts:
            separator = " "
            content = separator.join(parts)
            self.update(content)
        else:
            self.update("")

    def set_polling_status(self, enabled: bool) -> None:
        """Update polling status indicator."""
        self._polling_status = "ON" if enabled else "OFF"
        self._update_content()

    def set_selected_devices(self, count: int) -> None:
        """Update selected devices count."""
        self._selected_devices = count
        self._update_content()


class TimeModule(FooterModule):
    """
    Module displaying current time.

    Shows current time in HH:MM:SS format.
    """

    def on_mount(self) -> None:
        """Initialize and start updates."""
        # Only start updates if properly mounted
        if self.is_mounted:
            self.start_updates(1.0)
            self._update()

    def _update(self) -> None:
        """Update time display."""
        if not self.is_mounted:
            return
        time_str = time.strftime('%H:%M:%S')
        self.update(f"[#888888]{time_str}[/]")


class UptimeModule(FooterModule):
    """
    Module displaying application uptime.

    Shows uptime in HH:MM:SS format.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.now()

    def on_mount(self) -> None:
        """Initialize and start updates."""
        # Only start updates if properly mounted
        if self.is_mounted:
            self.start_updates(1.0)
            self._update()

    def _update(self) -> None:
        """Update uptime display."""
        if not self.is_mounted:
            return
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.update(f"[#6a8a8a]UP:{uptime_str}[/]")


class CounterModule(FooterModule):
    """
    Module displaying a counter/label.

    Generic counter for displaying counts with labels.
    Example: "Devices: 5", "Errors: 0"
    """

    def __init__(self, label: str = "", value: int = 0, color: str = "#888888", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.color = color

    def set_value(self, value: int) -> None:
        """Update the counter value."""
        self.value = value
        self._update_content()

    def increment(self, amount: int = 1) -> None:
        """Increment the counter."""
        self.value += amount
        self._update_content()

    def _update_content(self) -> None:
        """Update the counter display."""
        self.update(f"[{self.color}]{self.label}:{self.value}[/]")


class SeparatorModule(FooterModule):
    """
    Visual separator for footer modules.

    Displays a vertical separator line.
    """

    def on_mount(self) -> None:
        """Initialize the separator on mount."""
        if self.is_mounted:
            self._update_content()

    def _update_content(self) -> None:
        """Update the separator."""
        # Only update if properly mounted to avoid layout issues
        if self.is_mounted:
            self.update("[#444444]│[/]")


class TextModule(FooterModule):
    """
    Simple text module for custom messages.

    Displays static or dynamic text content.
    """

    def __init__(self, text: str = "", color: str = "#888888", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.color = color

    def set_text(self, text: str) -> None:
        """Update the text content."""
        self.text = text
        self._update_content()

    def _update_content(self) -> None:
        """Update the text."""
        self.update(f"[{self.color}]{self.text}[/]")
