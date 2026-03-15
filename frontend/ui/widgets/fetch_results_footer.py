"""
fetch_results_footer.py
───────────────────────
Dedicated footer widget for the fetch results screen.

Uses the modular footer system with global shortcuts plus fetch-specific shortcuts.
"""

from frontend.ui.widgets.modular_footer import ModularFooter


class FetchResultsFooter(ModularFooter):
    """
    Fetch results footer with global and screen-specific shortcuts.

    Global: [b] dashboard │ [m] device management │ [p] prism │ [h] help │ [q] quit
    Extra (fetch-specific): [r] refresh, [b] back (shown in blue)
    """

    def __init__(self, **kwargs):
        # Define fetch results specific shortcuts (shown in blue)
        extra_shortcuts = [
            ("r", "refresh"),
            ("b", "back"),
        ]
        super().__init__(extra_shortcuts=extra_shortcuts, **kwargs)
