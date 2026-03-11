"""
focus_panel.py
──────────────
Reusable focusable panel widget with border-title support and color variants.
"""

from textual.containers import Container
from textual import events
from textual.widgets import Static


class FocusableStatic(Static):
    """
    A Static widget that passes clicks to its parent FocusPanel.

    Used as a base class for child widgets that need to make their parent
    focusable when clicked.
    """

    def on_click(self, event: events.Click) -> None:
        """Pass click to parent to focus the panel."""
        if self.parent:
            self.parent.focus()
        event.stop()


class FocusPanel(Container):
    """
    A reusable focusable panel container with border-title support.

    Features:
    - Automatic border-title styling
    - Click-to-focus behavior (via can_focus = True)
    - Visual feedback on focus (cyan border via CSS :focus selector)
    - Color variants via CSS classes (default: blue title, orange: orange title)
    - Consistent styling across all panels

    Usage:
        # Default (blue title)
        with FocusPanel("Sessions", id="sessions-panel"):
            yield DeviceList(id="device-list")

        # Orange variant (for realtime screens)
        with FocusPanel("Devices", id="devices-panel", classes="panel-orange"):
            yield DeviceList(id="device-list")

    CSS Classes:
    - panel-orange: Orange title variant for realtime screens
    - panel-green: Green title variant (future use)
    - panel-red: Red title variant (future use)

    The panel uses can_focus = True to receive focus directly, triggering
    CSS :focus selectors for the cyan border effect.
    """

    # Make the panel focusable
    can_focus = True

    def __init__(self, title: str = "", **kwargs):
        super().__init__(**kwargs)
        self._panel_title = title

    def on_mount(self) -> None:
        """Initialize the panel with border-title."""
        if self._panel_title:
            self.border_title = self._panel_title

    def on_click(self, event: events.Click) -> None:
        """
        Handle click events - focus the panel.

        Since can_focus = True, clicking anywhere in the panel focuses it,
        triggering the CSS :focus selector for cyan border styling.
        """
        self.focus()
        event.stop()
