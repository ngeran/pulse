"""
device_management_footer.py
───────────────────────────
Dedicated footer widget for the device management screen.

Uses the modular footer system with global shortcuts plus device management specific shortcuts.
"""

from frontend.ui.widgets.modular_footer import ModularFooter


class DeviceManagementFooter(ModularFooter):
    """
    Device management footer with global and screen-specific shortcuts.

    Global: [b] dashboard │ [f] facts │ [m] device management │ [p] prism │ [h] help │ [q] quit
    Extra (device-specific): [x] delete (shown in blue)
    """

    def __init__(self, **kwargs):
        # Define device management specific shortcuts (shown in blue)
        extra_shortcuts = [
            ("x", "delete"),
        ]
        super().__init__(extra_shortcuts=extra_shortcuts, **kwargs)
