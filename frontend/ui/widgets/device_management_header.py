"""
device_management_header.py
────────────────────────────
Dedicated header widget for the device management screen.
"""

import time
from datetime import datetime, timedelta
from textual.widgets import Static
from textual.reactive import reactive


class DeviceManagementHeader(Static):
    """Dedicated header showing device management status."""

    # Reactive properties for status updates
    ws_status = reactive("DISCONNECTED")
    api_status = reactive("INACTIVE")
    total_devices = reactive(0)
    connected_devices = reactive(0)
    failed_devices = reactive(0)
    filter_mode = reactive("BOTH")  # BOTH, DEVICES, INTERFACES

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.now()
        self._timer = None
        self._status_timer = None
        # Set initial content immediately
        self.update("DEVICE MANAGEMENT INITIALIZED")

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

        # Title field
        fields.append(self._get_title_field())

        # WS field
        fields.append(self._get_ws_field())

        # API field
        fields.append(self._get_api_field())

        # Total devices field
        fields.append(self._get_total_devices_field())

        # Connected devices field
        fields.append(self._get_connected_devices_field())

        # Failed devices field
        fields.append(self._get_failed_devices_field())

        # Filter mode field
        fields.append(self._get_filter_mode_field())

        # Uptime field
        fields.append(self._get_uptime_field())

        # Timestamp field
        fields.append(f"[#ffffff]{self._get_current_time()}[/]")

        # Join all fields with separator and space on both sides
        separator = " │ "
        header_line = separator.join(fields)

        try:
            self.update(header_line)
        except Exception:
            # If update fails, at least show basic content
            self.update("DEVICE MANAGEMENT │ WS │ API │ Total: 0 │ Connected: 0 │ Failed: 0")

    def _get_title_field(self) -> str:
        """Get the title field with blue background."""
        return "[#ffffff on #0088ff] DEVICE MANAGEMENT [/]"

    def _get_ws_field(self) -> str:
        """Get the WS field with status-based color."""
        ws_color = "#008800" if self.ws_status == "CONNECTED" else "#ff0000"
        status_label = "ONLINE" if self.ws_status == "CONNECTED" else "OFFLINE"
        return f"[#ffffff on {ws_color}] {status_label} [/]"

    def _get_api_field(self) -> str:
        """Get the API field with status-based color."""
        if self.api_status == "ACTIVE":
            api_color = "#008800"
        elif self.api_status == "INACTIVE":
            api_color = "#ff8800"
        else:  # DOWN
            api_color = "#ff0000"
        return f"[#ffffff on {api_color}] {self.api_status} [/]"

    def _get_total_devices_field(self) -> str:
        """Get the total devices field."""
        return f"[#ffffff]Total:{self.total_devices}[/]"

    def _get_connected_devices_field(self) -> str:
        """Get the connected devices field with green color."""
        return f"[#00ff00]Connected:{self.connected_devices}[/]"

    def _get_failed_devices_field(self) -> str:
        """Get the failed devices field with red color."""
        return f"[#ff0000]Failed:{self.failed_devices}[/]"

    def _get_filter_mode_field(self) -> str:
        """Get the filter mode field."""
        return f"[#ffffff]{self.filter_mode}[/]"

    def _get_uptime_field(self) -> str:
        """Get the uptime field with blue color."""
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"[#0088ff]UP:{uptime_str}[/]"

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
                sessions = app.conn_mgr.sessions
                total = len(sessions)
                connected = sum(
                    1 for session in sessions.values()
                    if hasattr(session, 'state') and session.state.value == "CONNECTED"
                )
                failed = sum(
                    1 for session in sessions.values()
                    if hasattr(session, 'state') and session.state.value == "FAILED"
                )

                self.total_devices = total
                self.connected_devices = connected
                self.failed_devices = failed
                self.set_api_status("ACTIVE" if connected > 0 else "INACTIVE")
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

    def set_device_counts(self, total: int, connected: int, failed: int) -> None:
        """Update device counts and refresh."""
        self.total_devices = total
        self.connected_devices = connected
        self.failed_devices = failed
        self.update_content()

    def set_filter_mode(self, mode: str) -> None:
        """Update filter mode and refresh."""
        self.filter_mode = mode
        self.update_content()
