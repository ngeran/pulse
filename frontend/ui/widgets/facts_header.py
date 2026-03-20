"""
facts_header.py
───────────────
Modular header for the Facts screen.

Displays:
- Screen title
- Global status (WS, API)
- Last poll time
"""

from datetime import datetime
from frontend.ui.widgets.modular_header import ModularHeader


class FactsHeader(ModularHeader):
    """Header showing facts screen information."""

    def __init__(self, title: str, **kwargs):
        super().__init__(title, **kwargs)
        self._last_poll = None

    def set_device_count(self, count: int) -> None:
        """Set the device count (not used in Facts)."""
        pass

    def update_last_poll(self) -> None:
        """Update the last poll timestamp."""
        self._last_poll = datetime.now()
        self.update_status()

    def _get_last_poll_time(self) -> str:
        """Get formatted last poll time."""
        if not self._last_poll:
            return "Never"

        now = datetime.now()
        diff = (now - self._last_poll).total_seconds()

        if diff < 60:
            return "Just now"
        elif diff < 3600:
            mins = int(diff / 60)
            return f"{mins}m ago"
        else:
            return self._last_poll.strftime("%H:%M:%S")

    def update_status(self) -> None:
        """Update the header content."""
        # First update global status (WS, API) from parent
        self._update_global_status()

        # Build global status fields (WS, API)
        if self._ws_status == "ONLINE":
            ws_field = "[#5aba5a on #2a4a2a] WS [/]"
        else:
            ws_field = "[#ba5a5a on #4a2a2a] WS [/]"

        if self._api_status == "ACTIVE":
            api_field = "[#5aba5a on #2a4a2a] API [/]"
        elif self._api_status == "INACTIVE":
            api_field = "[#ba8a5a on #4a3a2a] API [/]"
        else:  # DOWN
            api_field = "[#ba5a5a on #4a2a2a] API [/]"

        # Build Facts-specific fields
        last_poll_str = self._get_last_poll_time()
        poll_field = f"[#888888]Last poll:[#c2c0b6] {last_poll_str}[/]"

        # Combine all fields: WS, API, Poll time
        separator = " │ "
        status_content = separator.join([
            ws_field,
            api_field,
            poll_field
        ])

        # Set status content using the base class method
        self._set_status_content(status_content)
