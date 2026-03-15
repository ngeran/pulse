"""
help_screen.py
──────────────
Help screen displaying all keyboard shortcuts and app usage.

Accessible from anywhere with [h] key.
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from pathlib import Path
from frontend.ui.widgets.help_footer import HelpFooter


class HelpScreen(Screen):
    """Modal help screen with keyboard shortcuts and usage instructions."""

    # Load stylesheet
    _CSS = Path(__file__).parent.parent / "styles" / "help_screen.tcss"
    _MODULAR_FOOTER_CSS = Path(__file__).parent.parent / "styles" / "modular_footer.tcss"

    CSS = ""
    if _CSS.exists():
        CSS += _CSS.read_text()
    if _MODULAR_FOOTER_CSS.exists():
        CSS += _MODULAR_FOOTER_CSS.read_text()

    BINDINGS = [
        ("escape,q,?", "app.pop_screen", "Close Help"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Vertical(id="help-container"):
            # Title
            yield Static("🔧 PULSE - KEYBOARD SHORTCUTS", id="help-title")

            # Global Shortcuts section
            yield Static("GLOBAL SHORTCUTS", id="help-header-global")
            yield Static(
                "[b] Dashboard      View main dashboard\n"
                "[m] Device Mgr     Device management screen\n"
                "[p] PRISM          Probe monitoring (RPM)\n"
                "[h] Help           Show this help screen\n"
                "[q] Quit           Exit application\n",
                id="help-global"
            )

            # Device Management section
            yield Static("DEVICE MANAGEMENT", id="help-header-dm")
            yield Static(
                "[c] Connect        Open connection dialog\n"
                "[d] Disconnect     Disconnect selected device\n"
                "[f] Fetch          Fetch data from devices\n"
                "[x] Delete         Remove failed sessions\n"
                "[p] Toggle Polling Enable/disable polling\n"
                "[s] Fiber Mode     Cycle fiber mode (SM/MM/Both)\n"
                "[r] Rescan         Rescan SFP transceivers\n"
                "[↑/↓] Navigate     Move cursor in device list\n"
                "[enter] Select      Select highlighted device",
                id="help-dm"
            )

            # PRISM section
            yield Static("PRISM", id="help-header-prism")
            yield Static(
                "[r] Refresh        Refresh probe data\n"
                "[b/m] Back         Return to previous screen\n"
                "[1-9] Tabs         Quick navigate to tabs\n"
                "[↑/↓/←/→] Navigate Move through probes",
                id="help-prism"
            )

            # Fetch Results section
            yield Static("FETCH RESULTS", id="help-header-fetch")
            yield Static(
                "[r] Refresh        Refresh current tab data\n"
                "[b/q/escape] Back  Return to device management\n"
                "[1-9] Tabs         Quick switch to data type",
                id="help-fetch"
            )

        # Modular footer with global shortcuts and help-specific shortcuts
        yield HelpFooter()
