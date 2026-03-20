"""
facts_footer.py
───────────────
Modular footer for the Facts screen.

Displays global shortcuts and facts-specific shortcuts.
"""

from frontend.ui.widgets.modular_footer import ModularFooter
from frontend.ui.widgets.shortcuts_widget import GlobalShortcutsWidget


class FactsFooter(ModularFooter):
    """
    Footer for the Facts screen with global and screen-specific shortcuts.

    Global: [b] dashboard │ [f] facts │ [m] device management │ [p] prism │ [h] help │ [q] quit
    Extra: [tab] panels │ [r] refresh
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Facts-specific shortcuts
        self.facts_shortcuts = [
            ("tab", "panels"),
            ("r", "refresh"),
        ]

    def compose(self):
        """Compose the footer with shortcuts."""
        # Left side: global shortcuts + facts-specific shortcuts
        from textual.widgets import Static

        yield GlobalShortcutsWidget(
            id="facts-footer-shortcuts",
            extra_shortcuts=self.facts_shortcuts
        )

        # Right side: time/uptime
        yield Static(id="facts-footer-time")
