from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label
from textual.containers import Vertical, Horizontal
import asyncio

class ConnectionScreen(ModalScreen):
    """A modal screen for entering device connection details."""
    
    DEFAULT_CSS = """
    ConnectionScreen {
        align: center middle;
        background: #000000;
    }

    #connection-panel {
        width: 60;
        height: auto;
        border: solid #2a2a2a;
        background: #000000;
        padding: 1 2;
    }

    #title {
        color: #4a4a4a;
        text-style: bold;
        text-align: center;
        margin-top: 0;
        background: #000000;
    }

    Label {
        color: #888888;
        margin-top: 1;
        background: #000000;
    }

    Input {
        margin-bottom: 1;
        border: solid #2a2a2a;
        background: #0a0a0a;
        color: #cccccc;
    }

    Input:focus {
        border: solid #3a3a3a;
        background: #111111;
    }

    #button-row {
        margin-top: 1;
        align: center middle;
        height: auto;
        background: #000000;
    }

    Button {
        margin: 0 1;
        background: #1a1a1a;
        border: solid #444444;
        color: #aaaaaa;
        text-style: none;
    }

    Button:hover {
        background: #2a2a2a;
        border: solid #555555;
        color: #cccccc;
    }

    Button.-success {
        background: #1a2a1a;
        border: solid #3a6a3a;
        color: #5aba5a;
        text-style: none;
    }

    Button.-success:hover {
        background: #2a3a2a;
        border: solid #4a7a4a;
        color: #6aca6a;
    }

    Button.-error {
        background: #2a1a1a;
        border: solid #6a3a3a;
        color: #ba5a5a;
        text-style: none;
    }

    Button.-error:hover {
        background: #3a2a2a;
        border: solid #7a4a4a;
        color: #ca6a6a;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="connection-panel"):
            yield Label("Add Juniper Devices", id="title")
            
            yield Label("IP/Host (comma-separated for multiple)")
            yield Input(placeholder="e.g. 172.27.200.200, 172.27.200.201", id="hosts")
            
            yield Label("Username")
            yield Input(placeholder="admin", id="username")
            
            yield Label("Password")
            yield Input(placeholder="password", password=True, id="password")
            
            with Horizontal(id="button-row"):
                yield Button("Cancel", variant="error", id="cancel")
                yield Button("Connect", variant="success", id="connect")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "connect":
            hosts_str = self.query_one("#hosts", Input).value
            username = self.query_one("#username", Input).value
            password = self.query_one("#password", Input).value
            
            if not hosts_str or not username or not password:
                return # Should probably show a warning, but for now just ignore
            
            # Parse hosts
            hosts = [h.strip() for h in hosts_str.split(",") if h.strip()]
            
            # Return credentials to the app
            self.dismiss({
                "hosts": hosts,
                "username": username,
                "password": password
            })
