import sys
import os
from frontend.ui.app import PulseApp

def main():
    # Check for --dev flag
    if "--dev" in sys.argv:
        # Enable Textual development mode with hot CSS reloading
        os.environ["TEXTUAL"] = "dev"

    app = PulseApp()
    app.run()

if __name__ == "__main__":
    main()
