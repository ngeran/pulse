"""
device_management_header.py
────────────────────────────
Dedicated header widget for the device management screen.

Extends ModularHeader to show device management specific status:
WS, API, Total, Connected, Failed, Filter mode, Uptime, Timestamp
"""

from textual.widgets import Static
from textual.app import ComposeResult
import time
from datetime import datetime
from frontend.ui.widgets.modular_header import ModularHeader


class DeviceManagementHeader(ModularHeader):
    """
    Device management header with dynamic title and status fields.

    Shows: WS │ API │ Total │ Connected │ Failed │ Filter │ UP:time │ timestamp
    """

    def __init__(self, title: str = "DEVICE MANAGEMENT", **kwargs):
        super().__init__(title, **kwargs)
        self._start_time = datetime.now()
        self._ws_status = "OFFLINE"
        self._api_status = "INACTIVE"
        self._total = 0
        self._connected = 0
        self._failed = 0
        self._filter_mode = "BOTH"

    def compose(self) -> ComposeResult:
        """Compose the header with title and status fields."""
        # Use parent's compose to maintain compatibility
        yield from super().compose()

    def _set_status_content(self, content: str) -> None:
        """
        Set the status field content.

        Override to use the legacy ID for backward compatibility.
        """
        try:
            # Try the new ID first (from base class)
            status_widget = self.query_one("#header-status", Static)
            status_widget.update(content)
        except Exception:
            try:
                # Fall back to legacy ID for compatibility
                status_widget = self.query_one("#dm-status-fields", Static)
                status_widget.update(content)
            except Exception:
                pass

    def update_status(self) -> None:
        """Update the status fields display."""
        # Update global status (WS, API) using parent method
        self._update_global_status()

        # Update device counts
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

        # Build status content
        # WebSocket status
        if self._ws_status == "ONLINE":
            ws_field = "[#5aba5a on #2a4a2a] WS [/]"
        else:
            ws_field = "[#ba5a5a on #4a2a2a] WS [/]"

        # API status
        if self._api_status == "ACTIVE":
            api_field = "[#5aba5a on #2a4a2a] API [/]"
        elif self._api_status == "INACTIVE":
            api_field = "[#ba8a5a on #4a3a2a] API [/]"
        else:  # DOWN
            api_field = "[#ba5a5a on #4a2a2a] API [/]"

        # Device counts
        total_field = f"[#888888]Total:{self._total}[/]"
        connected_field = f"[#5aba5a]Connected:{self._connected}[/]"
        failed_field = f"[#ba5a5a]Failed:{self._failed}[/]"

        # Filter mode
        filter_field = f"[#888888]{self._filter_mode}[/]"

        # Uptime
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        uptime_field = f"[#6a8a8a]UP:{uptime_str}[/]"

        # Timestamp
        time_str = time.strftime('%H:%M:%S')
        timestamp_field = f"[#888888]{time_str}[/]"

        # Combine all fields
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

        # Set status content using the base class method
        self._set_status_content(status_content)

    def set_device_counts(self, total: int, connected: int, failed: int) -> None:
        """Update device counts and refresh display."""
        self._total = total
        self._connected = connected
        self._failed = failed
        self.update_status()

    def set_filter_mode(self, mode: str) -> None:
        """Update filter mode and refresh display."""
        self._filter_mode = mode
        self.update_status()

    def set_title(self, title: str) -> None:
        """Update the title dynamically."""
        try:
            from frontend.ui.widgets.title_field import TitleField
            title_widget = self.query_one("#dm-title", TitleField)
            title_widget.set_title(title)
        except Exception:
            pass
