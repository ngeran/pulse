"""
device_management_footer.py
───────────────────────────
Dedicated footer widget for the device management screen.
"""

import time
from textual.widgets import Static


class DeviceManagementFooter(Static):
    """Dedicated footer for the device management screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set initial content immediately
        self.update("DEVICE MANAGEMENT FOOTER INITIALIZED")

    def on_mount(self) -> None:
        """Initialize the footer content."""
        self.update_content()
        # Update every second
        self._timer = self.set_interval(1, self.update_content)

    def update_content(self) -> None:
        """Update the footer display."""
        try:
            width = self.app.size.width
        except:
            width = 140

        # Current time
        current_time = time.strftime('%H:%M:%S')

        # Help text
        help_text = "Press 'c' to add devices | 'd' to disconnect selected | 'f' to fetch data | 'p' to toggle polling | 'q' to quit"

        # Calculate spacing
        left_text = f"{help_text}"
        right_text = f"{current_time}"

        spacing = width - len(left_text) - len(right_text) - 4

        footer_content = f"{left_text}{' ' * max(0, spacing)}{right_text}"

        try:
            self.update(footer_content)
        except Exception:
            self.update(help_text)
