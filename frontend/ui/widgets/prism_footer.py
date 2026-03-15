"""
prism_footer.py
───────────────
Dedicated footer widget for the PRISM screen.

Uses the modular footer system with global shortcuts only.
"""

from frontend.ui.widgets.modular_footer import ModularFooter


class PrismFooter(ModularFooter):
    """
    PRISM footer with global shortcuts and panel/probe navigation.

    Global: [b] dashboard │ [m] device management │ [p] prism │ [h] help │ [q] quit
    Extra: [tab] panels │ [up/down] navigate │ [enter] details
    """

    def __init__(self, **kwargs):
        # Add panel and probe table navigation shortcuts
        extra_shortcuts = [
            ("tab", "panels"),
            ("up/down", "navigate"),
            ("enter", "details"),
        ]
        super().__init__(extra_shortcuts=extra_shortcuts, **kwargs)
