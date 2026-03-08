#!/usr/bin/env python3
"""Test health dashboard screen rendering."""

import sys
import asyncio
sys.path.insert(0, '.')

from textual.app import App
from frontend.ui.screens.health_dashboard import HealthDashboardScreen

class TestApp(App):
    """Test app to validate health dashboard screen."""
    CSS_PATH = "frontend/styles/dark.tcss"

    def on_mount(self):
        """Install and push the health dashboard screen."""
        try:
            self.install_screen(HealthDashboardScreen(), name='health')
            print("✓ Health dashboard screen installed")

            # Try to push the screen (this will trigger CSS rendering)
            self.push_screen('health')
            print("✓ Health dashboard screen pushed successfully")

            # Schedule a return to exit cleanly
            self.call_later(0.5, self.app_exit)

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            self.exit(1)

    def app_exit(self):
        """Exit the app."""
        self.exit()

if __name__ == "__main__":
    try:
        app = TestApp()
        print("✓ App created, testing screen rendering...")
        app.run()
        print("✓ Test completed successfully!")
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
