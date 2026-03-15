"""
device_list_widget.py
──────────────────────
Modular, reusable device list widget that displays connected devices.

Subscribes to connection events and automatically updates when devices
connect/disconnect. Can be used across multiple screens.
"""

from typing import Optional, Dict, List
from textual.widgets import Static
from textual.app import ComposeResult
from rich.text import Text
from frontend.ui.mixins.event_subscriber import EventSubscriberMixin


class DeviceListWidget(Static, EventSubscriberMixin):
    """
    Reusable device list widget that displays connected devices.

    Features:
    - Auto-updates when devices connect/disconnect
    - Shows device status with color coding
    - Cursor selection for device operations
    - Subscribes to backend connection events
    - Auto-unsubscribes on unmount (via EventSubscriberMixin)

    Usage:
        yield DeviceListWidget(id="my-device-list")
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._devices = {}
        self._conn_mgr = None
        self._device_list: List[str] = []  # Ordered list of device hostnames
        self._cursor_index: int = 0  # Currently selected device index

    async def on_mount(self) -> None:
        """Initialize the device list and subscribe to events."""
        # Get connection manager from app
        app = self.app
        if hasattr(app, 'conn_mgr'):
            self._conn_mgr = app.conn_mgr
            # Subscribe to connection events (async)
            self._event_subscription_id = await self._conn_mgr.subscribe_to_events(
                self._handle_connection_event
            )

        # Initial population
        self._refresh_from_sessions()

    def _handle_connection_event(self, event) -> None:
        """Handle backend connection events and update display."""
        try:
            from backend.core.events import EventMessage, ConnectionEvent

            if not isinstance(event, EventMessage):
                return

            # Update device list on connection events
            if event.event_type in [
                ConnectionEvent.CONNECTED,
                ConnectionEvent.DISCONNECTED,
                ConnectionEvent.STATE_CHANGED
            ]:
                self._refresh_from_sessions()
        except Exception:
            pass

    def _refresh_from_sessions(self) -> None:
        """Refresh the device list from current connection manager sessions."""
        if not self._conn_mgr:
            return

        # Build devices dict from sessions
        devices = {}
        for host, session in self._conn_mgr.sessions.items():
            status = session.state.value if hasattr(session, 'state') else "UNKNOWN"
            devices[host] = {
                "status": status,
            }

        self._devices = devices
        self._device_list = sorted(devices.keys(), key=lambda h: (
            0 if devices[h]["status"] == "CONNECTED" else 1,
            h
        ))

        # Reset cursor if out of bounds
        if self._cursor_index >= len(self._device_list):
            self._cursor_index = max(0, len(self._device_list) - 1)

        self._update_display()

    def _update_display(self) -> None:
        """Update the device list display with OLED-friendly colored circles and cursor."""
        content = Text()

        if not self._device_list:
            content.append("No devices", style="#666666")
        else:
            for idx, host in enumerate(self._device_list):
                info = self._devices[host]
                status = info.get("status", "UNKNOWN")
                is_selected = (idx == self._cursor_index)

                # OLED-friendly colors and circle icons
                if status == "CONNECTED":
                    if is_selected:
                        status_color = "#00d7ff"  # Blue for selected
                        status_icon = "●"  # Solid circle
                    else:
                        status_color = "#5aba5a"  # Dim green for connected
                        status_icon = "●"  # Solid circle
                elif status == "CONNECTING":
                    status_color = "#ba8a5a"  # Orange/amber
                    status_icon = "◌"  # Half-filled circle
                elif status == "FAILED":
                    status_color = "#ba5a5a"  # Dim red
                    status_icon = "✖"  # X mark
                else:  # DISCONNECTED or UNKNOWN
                    status_color = "#888888"  # Solid gray
                    status_icon = "●"  # Solid circle

                # Add newline if not first
                if idx > 0:
                    content.append("\n")

                # Add cursor indicator (blue if selected, gray if not)
                cursor_color = "#00d7ff" if is_selected else "#444444"
                content.append(f"> ", style=cursor_color)

                # Add device number
                number_color = "#00d7ff" if is_selected else "#888888"
                content.append(f"{idx + 1}. ", style=number_color)

                # Add device entry
                content.append(f"{status_icon} ", style=status_color)
                content.append(host)

        self.update(content)

    def get_selected_device(self) -> Optional[str]:
        """Get the currently selected device hostname."""
        if 0 <= self._cursor_index < len(self._device_list):
            return self._device_list[self._cursor_index]
        return None

    def cursor_up(self) -> None:
        """Move cursor up."""
        if self._cursor_index > 0:
            self._cursor_index -= 1
            self._update_display()

    def cursor_down(self) -> None:
        """Move cursor down."""
        if self._cursor_index < len(self._device_list) - 1:
            self._cursor_index += 1
            self._update_display()

    def get_devices(self) -> Dict[str, dict]:
        """Get the current device list."""
        return self._devices.copy()

    def refresh_devices(self) -> None:
        """Manually refresh the device list."""
        self._refresh_from_sessions()
