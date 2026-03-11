"""
Realtime Dashboard Screen
──────────────────────────
A new dashboard view with static header/footer and 3-column layout.
"""

from textual.widgets import Static, DataTable
from textual.containers import Horizontal, Vertical, Container
from textual.screen import Screen
from textual.app import ComposeResult
from pathlib import Path
from frontend.ui.widgets.realtime_header import RealtimeHeader
from frontend.ui.widgets.realtime_footer import RealtimeFooter
from frontend.ui.widgets.focus_panel import FocusPanel


class DeviceListWidget(Static):
    """Widget displaying the list of monitored devices."""

    def on_mount(self) -> None:
        """Initialize the device list."""
        self.update("[#666666]Device List[/]\n\n[dim]No devices connected[/]")


class InterfaceTableWidget(DataTable):
    """Widget displaying interface information in a table."""

    def on_mount(self) -> None:
        """Initialize the interface table."""
        self.add_columns("Interface", "Status", "RX Power", "TX Power", "Errors")
        self.cursor_type = "row"
        self.zebra_stripes = False  # Disabled for pure black background


class AlertTableWidget(DataTable):
    """Widget displaying active alerts."""

    def on_mount(self) -> None:
        """Initialize the alert table."""
        self.add_columns("Severity", "Device", "Interface", "Message", "Time")
        self.cursor_type = "row"
        self.zebra_stripes = False  # Disabled for pure black background


class DetailPanelWidget(Static):
    """Widget showing detailed information for selected items."""

    def on_mount(self) -> None:
        """Initialize the detail panel."""
        self.update("[#666666]Details[/]\n\n[dim]Select an item to view details[/]")


class RealtimeDashboardScreen(Screen):
    """A new dashboard screen with 3-column layout."""

    # Load all stylesheets
    _CSS_PATH_PANELS = Path(__file__).parent.parent / "styles" / "panels.tcss"
    _CSS_PATH_DASHBOARD = Path(__file__).parent.parent / "styles" / "realtime_dashboard.tcss"
    _CSS_PATH_FOOTER = Path(__file__).parent.parent / "styles" / "footer.tcss"

    _css_panels = _CSS_PATH_PANELS.read_text() if _CSS_PATH_PANELS.exists() else ""
    _css_dashboard = _CSS_PATH_DASHBOARD.read_text() if _CSS_PATH_DASHBOARD.exists() else ""
    _css_footer = _CSS_PATH_FOOTER.read_text() if _CSS_PATH_FOOTER.exists() else ""

    CSS = _css_panels + "\n" + _css_dashboard + "\n" + _css_footer

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        # Use Vertical container to ensure proper layout
        with Vertical(id="rt-container"):
            # Static header
            yield RealtimeHeader(id="rt-header")

            # Main content area with 3 columns
            with Horizontal(id="rt-main"):
                # Left column: Devices (orange variant)
                with FocusPanel("Devices", id="rt-left-wrap", classes="panel-orange"):
                    yield DeviceListWidget(id="rt-left")

                # Center column: Interfaces (top) and Alerts (bottom)
                with Vertical(id="rt-center"):
                    with FocusPanel("Interfaces", id="rt-itable-wrap", classes="panel-orange"):
                        yield InterfaceTableWidget(id="rt-interface-table")
                    with FocusPanel("Alerts", id="rt-alert-wrap", classes="panel-orange"):
                        yield AlertTableWidget(id="rt-alert-table")

                # Right column: Detail panel (orange variant)
                with FocusPanel("Detail", id="rt-right-wrap", classes="panel-orange"):
                    yield DetailPanelWidget(id="rt-right")

            # Footer
            yield RealtimeFooter(id="rt-footer")
