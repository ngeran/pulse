"""
device_list_widget.py
──────────────────────
Modular, reusable device list widget that displays connected devices.

Subscribes to connection events and automatically updates when devices
connect/disconnect. Can be used across multiple screens.
"""

from typing import Optional, Dict
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
    - Displays device hostname and connection state
    - Subscribes to backend connection events
    - Auto-unsubscribes on unmount (via EventSubscriberMixin)

    Usage:
        yield DeviceListWidget(id="my-device-list")
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._devices = {}
        self._conn_mgr = None

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
        self._update_display()

    def _update_display(self) -> None:
        """Update the device list display."""
        content = Text()

        if not self._devices:
            content.append("No devices", style="dim")
        else:
            # Sort by status (CONNECTED first) then by hostname
            sorted_devices = sorted(
                self._devices.items(),
                key=lambda x: (
                    0 if x[1]["status"] == "CONNECTED" else 1,
                    x[0]
                )
            )

            for idx, (host, info) in enumerate(sorted_devices):
                status = info.get("status", "UNKNOWN")

                # Color code by status
                if status == "CONNECTED":
                    status_color = "green"
                    status_icon = "●"
                elif status == "CONNECTING":
                    status_color = "yellow"
                    status_icon = "◌"
                elif status == "FAILED":
                    status_color = "red"
                    status_icon = "✖"
                else:  # DISCONNECTED or UNKNOWN
                    status_color = "grey58"
                    status_icon = "○"

                # Add device entry
                if idx > 0:
                    content.append("\n")

                content.append(f"{status_icon} ", style=status_color)
                content.append(f"{status} ", style=f"bold {status_color}")
                content.append(host)

        self.update(content)

    def get_devices(self) -> Dict[str, dict]:
        """Get the current device list."""
        return self._devices.copy()

    def refresh_devices(self) -> None:
        """Manually refresh the device list."""
        self._refresh_from_sessions()
