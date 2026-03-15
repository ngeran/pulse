"""
help_footer.py
──────────────
Dedicated footer widget for the help screen.

Uses the modular footer system with global shortcuts only.
"""

from frontend.ui.widgets.modular_footer import ModularFooter


class HelpFooter(ModularFooter):
    """
    Help footer with global shortcuts.

    Global: [b] dashboard │ [m] device management │ [p] prism │ [h] help │ [q] quit
    Extra (help-specific): [escape, q, ?] close help (shown in blue)
    """

    def __init__(self, **kwargs):
        # Define help specific shortcuts (shown in blue)
        extra_shortcuts = [
            ("escape, ?", "close help"),
        ]
        super().__init__(extra_shortcuts=extra_shortcuts, **kwargs)
