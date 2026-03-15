"""
dashboard_footer.py
───────────────────
Dedicated footer widget for the dashboard screen.

Uses the modular footer system with global shortcuts only.
"""

from frontend.ui.widgets.modular_footer import ModularFooter


class DashboardFooter(ModularFooter):
    """
    Dashboard footer with global shortcuts.

    Global: [b] dashboard │ [m] device management │ [p] prism │ [h] help │ [q] quit
    No extra shortcuts - uses only global shortcuts.
    """

    def __init__(self, **kwargs):
        # No extra shortcuts for dashboard - uses global only
        super().__init__(extra_shortcuts=None, **kwargs)
