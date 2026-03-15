"""
title_field.py
──────────────
Dynamic title widget that displays the screen name.
Reusable across different screens with dedicated styling.
"""

from textual.widgets import Static
from textual.reactive import reactive


class TitleField(Static):
    """
    Dynamic title widget for displaying screen names.

    The title text is passed as a parameter and displayed with
    consistent styling. Can be reused across different screens.

    Args:
        title: The title text to display (e.g., "DEVICE MANAGEMENT")
    """

    def __init__(self, title: str = "", **kwargs):
        super().__init__(**kwargs)
        self._title = title
        self._update_display()

    def set_title(self, title: str) -> None:
        """Update the title text and refresh display."""
        self._title = title
        self._update_display()

    def _update_display(self) -> None:
        """Update the title display."""
        if not self._title:
            self.update("")
            return

        # Render title with pure black OLED-friendly styling
        # Dark gray background with dim white text
        title_content = f"[#aaaaaa on #1a1a1a] {self._title} [/]"
        self.update(title_content)
