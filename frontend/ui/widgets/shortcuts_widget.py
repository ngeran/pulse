"""
shortcuts_widget.py
──────────────────
Global shortcuts widget for footers.

Displays the main navigation shortcuts consistently across all screens.
"""

from textual.widgets import Static
from textual.app import ComposeResult
from datetime import datetime
import time


class GlobalShortcutsWidget(Static):
    """
    Widget displaying global navigation shortcuts.

    Shows: [b] dashboard │ [f] facts │ [m] device management │ [p] prism │ [h] help │ [q] quit
    Can be extended with screen-specific shortcuts (shown in blue with [x]).
    """

    def __init__(self, extra_shortcuts=None, **kwargs):
        super().__init__(**kwargs)
        # Core global shortcuts
        self._shortcuts = [
            ("b", "dashboard"),
            ("f", "facts"),
            ("m", "device management"),
            ("p", "prism"),
            ("h", "help"),
            ("q", "quit"),
        ]
        # Extra shortcuts (screen-specific, will be shown in blue)
        self._extra_shortcuts = extra_shortcuts or []

    def on_mount(self) -> None:
        """Initialize the shortcuts display."""
        self._update_content()

    def _update_content(self) -> None:
        """Update the shortcuts display using Rich Text for proper bracket rendering."""
        from rich.text import Text

        content = Text()
        separator = " │ "

        # Add global shortcuts
        for idx, (key, desc) in enumerate(self._shortcuts):
            # Add the bracket notation with blue styling
            content.append(f"[{key}]", style="bold #00d7ff")
            content.append(f" {desc}", style="default")

            # Add separator between items (but not after the last one)
            if idx < len(self._shortcuts) - 1 or self._extra_shortcuts:
                content.append(separator, style="dim")

        # Add extra shortcuts (screen-specific, in blue)
        for idx, (key, desc) in enumerate(self._extra_shortcuts):
            # Add the bracket notation with blue styling
            content.append(f"[{key}]", style="bold #00d7ff")
            content.append(f" {desc}", style="#00d7ff")

            # Add separator between items (but not after the last one)
            if idx < len(self._extra_shortcuts) - 1:
                content.append(separator, style="dim")

        self.update(content)

    def set_extra_shortcuts(self, shortcuts: list) -> None:
        """
        Set screen-specific extra shortcuts (shown in blue).

        Args:
            shortcuts: List of (key, description) tuples for screen-specific actions
        """
        self._extra_shortcuts = shortcuts
        self._update_content()
