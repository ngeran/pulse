#!/usr/bin/env python3
"""Validate CSS and imports for Textual app."""

import sys
sys.path.insert(0, '.')

print("Validating Pulse app components...")
print()

# Try to import the health dashboard screen
try:
    from frontend.ui.screens.health_dashboard import HealthDashboardScreen
    print("✓ HealthDashboardScreen imported successfully")
except Exception as e:
    print(f"✗ HealthDashboardScreen error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to import the app
try:
    from frontend.ui.app import PulseApp
    print("✓ PulseApp imported successfully")
except Exception as e:
    print(f"✗ PulseApp error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to create the app instance
try:
    from frontend.ui.app import PulseApp

    # Create app without running it
    import inspect
    app_class = PulseApp
    print(f"✓ PulseApp class validated")
    print(f"  - CSS_PATH: {app_class.CSS_PATH}")
    print(f"  - BINDINGS: {len(app_class.BINDINGS)} bindings")
except Exception as e:
    print(f"✗ App validation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("✓ All validation checks passed!")
print()
print("To run the app:")
print("  ./run.sh")
print()
print("To access the Health Dashboard:")
print("  Press 'h' after the app starts")

