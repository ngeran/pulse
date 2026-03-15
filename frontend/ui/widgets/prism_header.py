"""
prism_header.py
──────────────
Dedicated header widget for the PRISM screen.

Extends ModularHeader to show PRISM-specific status:
Devices, Probes, Polling interval, Last poll time, LIVE indicator
"""

from textual.app import ComposeResult
from datetime import datetime, timedelta
from frontend.ui.widgets.modular_header import ModularHeader


class PrismHeader(ModularHeader):
    """
    PRISM header with dynamic title and probe status.

    Shows: Devices: X │ Probes: Y │ Polling interval: Zs │ Last poll: X ago │ ● LIVE
    """

    def __init__(self, title: str = "PRISM", **kwargs):
        super().__init__(title, **kwargs)
        self._device_count = 0
        self._probe_count = 0
        self._polling_interval = 5
        self._last_poll = None
        self._is_live = True

    def update_status(self) -> None:
        """Update the PRISM status fields display."""
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

        # Build PRISM-specific status fields
        devices_field = f"[#888888]Devices:[#c2c0b6] {self._device_count}[/]"
        probes_field = f"[#888888]Probes:[#c2c0b6] {self._probe_count}[/]"
        interval_field = f"[#888888]Polling interval:[#c2c0b6] {self._polling_interval}s[/]"

        # Last poll time
        last_poll_str = self._get_last_poll_time()
        last_poll_field = f"[#888888]Last poll:[#c2c0b6] {last_poll_str} ago[/]"

        # LIVE indicator
        if self._is_live:
            live_indicator = "[#5aba5a]● LIVE[/]"
        else:
            live_indicator = "[#ba5a5a]○ OFFLINE[/]"

        # Combine all fields: WS, API, PRISM fields
        separator = " │ "
        status_content = separator.join([
            ws_field,
            api_field,
            devices_field,
            probes_field,
            interval_field,
            last_poll_field,
            live_indicator
        ])

        # Set status content using the base class method
        self._set_status_content(status_content)

    def _get_last_poll_time(self) -> str:
        """Get formatted time since last poll."""
        if not self._last_poll:
            return "00:00:00"
        delta = datetime.now() - self._last_poll
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def set_probe_stats(self, devices: int, probes: int, interval: int) -> None:
        """
        Update probe statistics.

        Args:
            devices: Number of devices being monitored
            probes: Total number of probes
            interval: Polling interval in seconds
        """
        self._device_count = devices
        self._probe_count = probes
        self._polling_interval = interval
        self.update_status()

    def update_last_poll(self) -> None:
        """Update the last poll timestamp to now."""
        self._last_poll = datetime.now()
        self.update_status()

    def set_live_status(self, is_live: bool) -> None:
        """
        Set the live/offline status.

        Args:
            is_live: True if polling is active, False otherwise
        """
        self._is_live = is_live
        self.update_status()
