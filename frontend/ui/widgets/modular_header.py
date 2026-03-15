"""
modular_header.py
─────────────────
Base class for modular headers across all screens.

Provides:
- Dynamic title field (left side)
- Extensible status area (right side)
- Timer management for auto-updates
- Consistent layout and styling
- Global WS and API status indicators
"""

from textual.widgets import Static
from textual.containers import Horizontal
from textual.app import ComposeResult
import time
from datetime import datetime
from frontend.ui.widgets.title_field import TitleField


class ModularHeader(Horizontal):
    """
    Base class for modular headers.

    All screen-specific headers should extend this class and override
    the update_status() method to provide their custom status content.

    Layout:
    [TitleField] │ [WS] │ [API] │ [Custom Status Content]

    All headers automatically show:
    - WS: WebSocket connection status (ONLINE/OFFLINE)
    - API: API activity status (ACTIVE/INACTIVE)
    """

    def __init__(self, title: str = "", **kwargs):
        super().__init__(**kwargs)
        self._title_text = title
        self._timer = None
        self._ws_status = "OFFLINE"
        self._api_status = "INACTIVE"

    def compose(self) -> ComposeResult:
        """Compose the header with title and status field."""
        yield TitleField(self._title_text, id="header-title")
        yield Static(id="header-status")

    def on_mount(self) -> None:
        """Initialize the header and start updates."""
        self.update_status()
        # Update every second by default (can be overridden)
        self._timer = self.set_interval(1, self._update_all)

    def _update_all(self) -> None:
        """Update all status fields and refresh display."""
        self.update_status()

    def update_status(self) -> None:
        """
        Update the status fields display.

        Subclasses should override this method to provide their specific
        status content. Should call self._set_status_content() with the
        formatted status string.
        """
        # Update global status indicators
        self._update_global_status()

        # Default implementation just shows WS and API status
        # Subclasses can extend this with additional fields
        status_content = self._get_global_status_content()
        self._set_status_content(status_content)

    def _update_global_status(self) -> None:
        """Update WebSocket and API status from the app."""
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

    def _get_global_status_content(self) -> str:
        """Get the global WS and API status content."""
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

        # Combine global status fields
        separator = " │ "
        return separator + separator.join([ws_field, api_field])

    def _set_status_content(self, content: str) -> None:
        """
        Set the status field content.

        Args:
            content: Formatted status content (can include Rich text markup)
        """
        try:
            status_widget = self.query_one("#header-status", Static)
            status_widget.update(content)
        except Exception:
            pass

    def set_title(self, title: str) -> None:
        """Update the title dynamically."""
        try:
            title_widget = self.query_one("#header-title", TitleField)
            title_widget.set_title(title)
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
