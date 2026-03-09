"""Test the realtime header widget"""
from textual.app import App, ComposeResult
from frontend.ui.widgets.realtime_header import RealtimeHeader

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield RealtimeHeader()

if __name__ == "__main__":
    app = TestApp()
    app.run()
