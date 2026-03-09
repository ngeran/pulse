"""
Test script to verify header and footer widgets render correctly
"""
from textual.app import App, ComposeResult
from frontend.ui.widgets.realtime_header import RealtimeHeader
from frontend.ui.widgets.realtime_footer import RealtimeFooter
from textual.containers import Vertical, Horizontal
from textual.widgets import Static


class TestApp(App):
    """Simple test app to verify header and footer."""

    CSS = """
    Screen {
        background: #000000;
    }
    RealtimeHeader {
        height: 1;
        background: #000000;
        border-bottom: solid #ff0000;
        padding: 0 1;
    }
    RealtimeHeader > Static {
        background: #000000;
        color: #ffffff;
        text-style: bold;
    }
    #main-content {
        height: 1fr;
        background: #000000;
        color: #ffffff;
        content-align: center middle;
    }
    RealtimeFooter {
        height: 1;
        background: #1a1a1a;
        border-top: solid #ff0000;
        padding: 0 1;
    }
    RealtimeFooter > Static {
        background: #1a1a1a;
        color: #888888;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the test layout."""
        yield RealtimeHeader()
        yield Static("MAIN CONTENT - This is the middle area", id="main-content")
        yield RealtimeFooter()


if __name__ == "__main__":
    app = TestApp()
    app.run()
