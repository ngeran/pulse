"""
dashboard.py
────────────
Main dashboard screen for the Pulse application.
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from pathlib import Path
from frontend.ui.widgets.device_management_header import DeviceManagementHeader
from frontend.ui.widgets.dashboard_footer import DashboardFooter


class DashboardScreen(Screen):
    """
    Main dashboard screen with modular layout.

    Features:
    - Dynamic header at top with screen title
    - Footer at bottom
    - Main content area in center
    """

    # Load stylesheets
    _SCREEN_CSS = Path(__file__).parent.parent / "styles" / "dashboard.tcss"
    _TITLE_CSS = Path(__file__).parent.parent / "styles" / "title_field.tcss"
    _MODULAR_FOOTER_CSS = Path(__file__).parent.parent / "styles" / "modular_footer.tcss"
    _MODULAR_HEADER_CSS = Path(__file__).parent.parent / "styles" / "modular_header.tcss"

    CSS = ""
    if _SCREEN_CSS.exists():
        CSS += _SCREEN_CSS.read_text()
    if _TITLE_CSS.exists():
        CSS += _TITLE_CSS.read_text()
    if _MODULAR_FOOTER_CSS.exists():
        CSS += _MODULAR_FOOTER_CSS.read_text()
    if _MODULAR_HEADER_CSS.exists():
        CSS += _MODULAR_HEADER_CSS.read_text()

    BINDINGS = [
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield DeviceManagementHeader("DASHBOARD", id="dashboard-header")

        with Horizontal(id="dashboard-main"):
            # Main content area - empty for now
            with Vertical(id="dashboard-content"):
                pass

        # Modular footer with global shortcuts
        yield DashboardFooter(id="dashboard-footer")
