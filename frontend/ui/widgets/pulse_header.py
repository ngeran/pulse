"""
pulse_header.py
───────────────
Custom header widget showing PULSE branding and connection status.
"""

import time
from textual.widgets import Static
from textual.reactive import reactive


class PulseHeader(Static):
    """Custom header showing PULSE branding and connection status."""

    ws_status = reactive("DISCONNECTED")
    backend_status = reactive("INACTIVE")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._timer = None

    def on_mount(self) -> None:
        """Set up a timer to update the timestamp every second."""
        self._timer = self.set_interval(1, self.update_content)
        self.update_status()
        # Also update status every 5 seconds to catch connection changes
        self._status_timer = self.set_interval(5, self.update_status)

    def update_content(self) -> None:
        """Update the display."""
        # Get terminal width from app
        try:
            width = self.app.size.width
        except:
            width = 140

        # Timestamp
        ts = f" {time.strftime('%Y-%m-%d %H:%M:%S')} "

        # Determine colors based on status
        ws_color = "#00ff00" if self.ws_status == "ONLINE" else "#ff0000"
        backend_color = "#00ff00" if self.backend_status == "ACTIVE" else "#ff0000"

        # Line 1: PULSE (orange) | CIRCUIT HEALTH MONITORING APP (red) with timestamp at right
        padding1 = width - 36 - len(ts) - 2
        line1 = f"[#ff8800]PULSE | [/#ff8800][#ff0000]CIRCUIT HEALTH MONITORING APP[/]{' ' * max(0, padding1)}[dim]{ts}[/]"

        # Line 2: Separator
        line2 = "[dim]─[/]" * (width - 1)

        # Line 3: Status from right (like curses W-48 position)
        # Calculate visible text length without markup
        visible_text = f"Websocket Status: {self.ws_status} │ Backend: {self.backend_status}"
        status_text = f"[dim]Websocket Status:[/] [{ws_color}]{self.ws_status}[/] [dim]│[/] [dim]Backend:[/] [{backend_color}]{self.backend_status}[/]"

        # Position 48 chars from right edge (like curses: W-48)
        # But we need to account for the visible text length
        status_padding = width - len(visible_text) - 2
        line3 = f"{' ' * max(0, status_padding)}{status_text}"

        # Line 4: Separator
        line4 = "[dim]─[/]" * (width - 1)

        self.update(f"{line1}\n{line2}\n{line3}\n{line4}")

    def update_status(self) -> None:
        """Update connection status from the app."""
        try:
            app = self.app

            # Check WebSocket connection - app has ws_connected attribute set by set_ws_status()
            ws_online = hasattr(app, 'ws_connected') and app.ws_connected
            self.set_ws_status("ONLINE" if ws_online else "DISCONNECTED")

            # Check backend device connections
            if hasattr(app, 'conn_mgr') and app.conn_mgr:
                connected_count = sum(
                    1 for session in app.conn_mgr.sessions.values()
                    if hasattr(session, 'state') and session.state.value == "CONNECTED"
                )
                self.set_backend_status("ACTIVE" if connected_count > 0 else "INACTIVE")
            else:
                self.set_backend_status("DOWN")

        except Exception as e:
            self.set_ws_status("DISCONNECTED")
            self.set_backend_status("INACTIVE")

    def set_ws_status(self, status: str) -> None:
        """Update WebSocket status and refresh."""
        self.ws_status = status
        self.update_content()

    def set_backend_status(self, status: str) -> None:
        """Update backend status and refresh."""
        self.backend_status = status
        self.update_content()
