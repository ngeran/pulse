"""
device_management_header.py
────────────────────────────
Dedicated header widget for the device management screen.

Features a dynamic TitleField widget for the screen name and a
status field that displays all status information.
"""

from textual.widgets import Static
from textual.containers import Horizontal
from textual.app import ComposeResult
import time
from datetime import datetime
from frontend.ui.widgets.title_field import TitleField


class DeviceManagementHeader(Horizontal):
    """
    Device management header with dynamic title and status fields.

    Layout:
    [TitleField] │ [StatusFields with WS/API/Counts/Uptime/Time]
    """

    def __init__(self, title: str = "DEVICE MANAGEMENT", **kwargs):
        super().__init__(**kwargs)
        self._title_text = title
        self._start_time = datetime.now()
        self._timer = None
        self._ws_status = "OFFLINE"
        self._api_status = "INACTIVE"
        self._total = 0
        self._connected = 0
        self._failed = 0
        self._filter_mode = "BOTH"

    def compose(self) -> ComposeResult:
        """Compose the header with title and status fields."""
        yield TitleField(self._title_text, id="dm-title")
        yield Static(id="dm-status-fields")

    def on_mount(self) -> None:
        """Initialize the header and start updates."""
        self._update_display()
        # Update every second
        self._timer = self.set_interval(1, self._update_all)

    def _update_all(self) -> None:
        """Update all status fields and refresh display."""
        self._update_status()
        self._update_device_counts()
        self._update_display()

    def _update_status(self) -> None:
        """Update WebSocket and API status."""
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

    def _update_device_counts(self) -> None:
        """Update device counts."""
        try:
            app = self.app
            if hasattr(app, 'conn_mgr') and app.conn_mgr:
                sessions = app.conn_mgr.sessions
                self._total = len(sessions)
                self._connected = sum(
                    1 for session in sessions.values()
                    if hasattr(session, 'state') and session.state.value == "CONNECTED"
                )
                self._failed = sum(
                    1 for session in sessions.values()
                    if hasattr(session, 'state') and session.state.value == "FAILED"
                )
        except Exception:
            pass

    def _update_display(self) -> None:
        """Update the status fields display."""
        # WebSocket status - show "WS" label with status color
        ws_color = "#008800" if self._ws_status == "ONLINE" else "#ff0000"
        ws_field = f"[#ffffff on {ws_color}] WS [/]"

        # API status - show "API" label with status color
        if self._api_status == "ACTIVE":
            api_color = "#008800"
        elif self._api_status == "INACTIVE":
            api_color = "#ff8800"
        else:  # DOWN
            api_color = "#ff0000"
        api_field = f"[#ffffff on {api_color}] API [/]"

        # Device counts
        total_field = f"[#ffffff]Total:{self._total}[/]"
        connected_field = f"[#00ff00]Connected:{self._connected}[/]"
        failed_field = f"[#ff0000]Failed:{self._failed}[/]"

        # Filter mode
        filter_field = f"[#ffffff]{self._filter_mode}[/]"

        # Uptime
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        uptime_field = f"[#0088ff]UP:{uptime_str}[/]"

        # Timestamp
        time_str = time.strftime('%H:%M:%S')
        timestamp_field = f"[#ffffff]{time_str}[/]"

        # Start with separator and combine all fields
        separator = " │ "
        status_content = separator + separator.join([
            ws_field,
            api_field,
            total_field,
            connected_field,
            failed_field,
            filter_field,
            uptime_field,
            timestamp_field
        ])

        try:
            status_widget = self.query_one("#dm-status-fields", Static)
            status_widget.update(status_content)
        except Exception:
            pass

    def set_device_counts(self, total: int, connected: int, failed: int) -> None:
        """Update device counts and refresh display."""
        self._total = total
        self._connected = connected
        self._failed = failed
        self._update_display()

    def set_filter_mode(self, mode: str) -> None:
        """Update filter mode and refresh display."""
        self._filter_mode = mode
        self._update_display()

    def set_title(self, title: str) -> None:
        """Update the title dynamically."""
        try:
            title_widget = self.query_one("#dm-title", TitleField)
            title_widget.set_title(title)
        except Exception:
            pass
