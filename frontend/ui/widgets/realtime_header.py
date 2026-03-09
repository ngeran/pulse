"""
realtime_header.py
──────────────────
Dedicated header widget for the realtime dashboard with status indicators.
"""

import time
from datetime import datetime, timedelta
from textual.widgets import Static
from textual.reactive import reactive


class RealtimeHeader(Static):
    """Dedicated header showing system uptime, errors, warnings, and connection status."""

    # Reactive properties for status updates
    ws_status = reactive("DISCONNECTED")
    api_status = reactive("DOWN")
    error_count = reactive(0)
    warning_count = reactive(0)
    session_count = reactive(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.now()
        self._timer = None
        self._status_timer = None
        # Set initial content immediately
        self.update("HEADER INITIALIZED")

    def on_mount(self) -> None:
        """Set up timers to update the header every second."""
        # Set initial content immediately
        self.update("INITIALIZING...")
        # Set up timer for content updates (every second)
        self._timer = self.set_interval(1, self.update_content)
        # Update status from app immediately
        self.update_status()
        # Set up timer for status updates (every 5 seconds)
        self._status_timer = self.set_interval(5, self.update_status)

    def update_content(self) -> None:
        """Update the header display."""
        try:
            width = self.app.size.width
        except:
            width = 140

        # Build each field separately
        fields = []

        # SYS-UP field
        fields.append(self._get_sys_up_field())

        # SES field
        fields.append(f"[#ffffff]SES:{self.session_count}[/]")

        # WS field
        fields.append(self._get_ws_field())

        # API field
        fields.append(self._get_api_field())

        # Title field
        fields.append(self._get_title_field())

        # ERR field
        fields.append(f"[#ff0000]ERR:{self.error_count}[/]")

        # WRN field
        fields.append(f"[#ff8800]WRN:{self.warning_count}[/]")

        # Timestamp field
        fields.append(f"[#ffffff]{self._get_current_time()}[/]")

        # Join all fields with separator and space on both sides
        separator = " │ "
        header_line = separator.join(fields)

        try:
            self.update(header_line)
        except Exception:
            # If update fails, at least show basic content
            self.update(f"SYS-UP │ SES:{self.session_count}│ WS│ API│ PULSE")

    def _get_sys_up_field(self) -> str:
        """Get the SYS-UP field with green background on label only."""
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"[#000000 on #008800] SYS-UP [/][#ffffff]  {uptime_str}[/]"

    def _get_ws_field(self) -> str:
        """Get the WS field with status-based color."""
        ws_color = "#008800" if self.ws_status == "CONNECTED" else "#ff0000"
        status_label = "ONLINE" if self.ws_status == "CONNECTED" else "OFFLINE"
        return f"[#000000 on {ws_color}] WS:{status_label} [/]"

    def _get_api_field(self) -> str:
        """Get the API field with status-based color."""
        if self.api_status == "ACTIVE":
            api_color = "#008800"
        elif self.api_status == "INACTIVE":
            api_color = "#ff8800"
        else:  # DOWN
            api_color = "#ff0000"
        return f"[#000000 on {api_color}] API:{self.api_status} [/]"

    def _get_title_field(self) -> str:
        """Get the title field."""
        return "[#ff8800]PULSE[/][#ffffff]-WAN CIRCUIT HEALTH MONITOR"

    def _get_current_time(self) -> str:
        """Get the current time string."""
        return time.strftime('%H:%M:%S')

    def update_status(self) -> None:
        """Update status from the app."""
        try:
            app = self.app

            # Check WebSocket connection
            ws_online = hasattr(app, 'ws_connected') and app.ws_connected
            self.set_ws_status("CONNECTED" if ws_online else "DISCONNECTED")

            # Check backend device connections
            if hasattr(app, 'conn_mgr') and app.conn_mgr:
                connected_count = sum(
                    1 for session in app.conn_mgr.sessions.values()
                    if hasattr(session, 'state') and session.state.value == "CONNECTED"
                )
                self.set_api_status("ACTIVE" if connected_count > 0 else "INACTIVE")
                self.session_count = connected_count
            else:
                self.set_api_status("DOWN")

        except Exception as e:
            self.set_ws_status("DISCONNECTED")
            self.set_api_status("INACTIVE")

    def set_ws_status(self, status: str) -> None:
        """Update WebSocket status and refresh."""
        self.ws_status = status
        self.update_content()

    def set_api_status(self, status: str) -> None:
        """Update API status and refresh."""
        self.api_status = status
        self.update_content()

    def set_error_count(self, count: int) -> None:
        """Update error count and refresh."""
        self.error_count = count
        self.update_content()

    def set_warning_count(self, count: int) -> None:
        """Update warning count and refresh."""
        self.warning_count = count
        self.update_content()
