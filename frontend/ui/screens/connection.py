from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label
from textual.containers import Vertical, Horizontal
from pathlib import Path
import asyncio

class ConnectionScreen(ModalScreen):
    """A modal screen for entering device connection details."""

    # Load dedicated stylesheet
    CSS = Path(__file__).parent.parent / "styles" / "connection_screen.tcss"

    if CSS.exists():
        CSS = CSS.read_text()

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
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Connect", variant="default", id="connect")

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
