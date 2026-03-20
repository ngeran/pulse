"""
facts.py
───────
Facts Screen - Display device facts and information

Shows comprehensive device information including:
- Device facts (model, serial, version, etc.)
- Interface summary
- System information
- Connected sessions status
"""

from typing import Optional, Dict, Any, List
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, DataTable
from textual.containers import Vertical, Horizontal, ScrollableContainer
from pathlib import Path
from rich.text import Text
from datetime import datetime
import asyncio

# Import modular header and footer
from frontend.ui.widgets.facts_header import FactsHeader
from frontend.ui.widgets.facts_footer import FactsFooter

# Import focusable panel system
from frontend.ui.widgets.focus_panel import FocusPanel, FocusableStatic


class FactsInfoPanel(FocusableStatic):
    """Panel displaying device information in a formatted way."""

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.data = {}
        self._auto_scroll = True

    def set_data(self, data: Dict[str, Any]) -> None:
        """Set the data to display."""
        self.data = data
        self._render_content()

    def _render_content(self) -> None:
        """Render the panel content."""
        text = Text()
        text.append(f"{self.title}\n", style="bold #00d7ff")
        text.append("─" * len(self.title) + "\n", style="dim #3a3a3a")

        if not self.data:
            text.append("\nNo data available.\n", style="dim #c2c0b6")
            self.update(text)
            return

        for key, value in self.data.items():
            # Format key
            key_str = f"\n{key}:"
            text.append(key_str, style="#c2c0b6")

            # Format value
            if isinstance(value, dict):
                text.append("\n", style="")
                for sub_key, sub_value in value.items():
                    text.append(f"  {sub_key}: ", style="dim #c2c0b6")
                    text.append(f"{sub_value}\n", style="#faf9f5")
            elif isinstance(value, list):
                text.append("\n", style="")
                for item in value:
                    text.append(f"  • {item}\n", style="#faf9f5")
            else:
                text.append(f" {value}\n", style="#faf9f5")

        self.update(text)


class DeviceSessionsTable(FocusableStatic):
    """Table displaying connected device sessions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sessions = []

    def set_sessions(self, sessions: Dict[str, Any]) -> None:
        """Set the sessions data to display."""
        self.sessions = []
        for host, session in sessions.items():
            self.sessions.append({
                "host": host,
                "state": session.state.value if hasattr(session.state, 'value') else str(session.state),
                "username": getattr(session, 'username', 'N/A'),
            })
        self._render_table()

    def _render_table(self) -> None:
        """Render the sessions table."""
        text = Text()

        # Column widths
        col_host = 30
        col_state = 12
        col_user = 20

        # Header row
        text.append(f"{'Device':<{col_host}}", style="#c2c0b6")
        text.append(f"{'State':<{col_state}}", style="#c2c0b6")
        text.append(f"{'Username':<{col_user}}", style="#c2c0b6")
        text.append("\n")

        # Separator line
        total_width = col_host + col_state + col_user
        text.append("─" * total_width + "\n", style="dim")

        # Data rows
        for session in self.sessions:
            # Device hostname
            text.append(f"{session['host']:<{col_host}}", style="#c2c0b6")

            # State with color
            state = session['state']
            if state == "CONNECTED":
                text.append(f"{state:<{col_state}}", style="#639922")  # GREEN
            elif state == "CONNECTING":
                text.append(f"{state:<{col_state}}", style="#EF9F27")  # YELLOW
            elif state == "FAILED":
                text.append(f"{state:<{col_state}}", style="#E24B4A")  # RED
            else:
                text.append(f"{state:<{col_state}}", style="#888888")  # GRAY

            # Username
            text.append(f"{session['username']:<{col_user}}", style="#c2c0b6")

            text.append("\n")

        if not self.sessions:
            text.append("\nNo connected devices.\n", style="dim #c2c0b6")

        self.update(text)


class FactsScreen(Screen):
    """Facts Screen - Display device and system information."""

    # Use CSS_PATH for live reloading in --dev mode
    CSS_PATH = Path(__file__).parent.parent / "styles" / "facts.tcss"

    BINDINGS = [
        ("b", "back", "Back to Dashboard"),
        ("q", "quit", "Quit Application"),
        ("r", "refresh", "Refresh Facts"),
        ("tab", "cycle_panels", "Cycle Panels"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._polling_task = None

    def compose(self) -> ComposeResult:
        """Compose the Facts screen."""
        # Facts header
        yield FactsHeader("FACTS", id="facts-header")

        with Vertical(id="facts-container"):
            # Device Sessions Panel (top)
            with FocusPanel("Connected Devices", id="facts-sessions-panel", classes="panel-orange"):
                yield DeviceSessionsTable(id="facts-sessions-table")

            # Information panels row (middle)
            with Horizontal(id="facts-info-panels"):
                # System Info Panel
                with FocusPanel("System Information", id="facts-system-panel", classes="panel-orange"):
                    yield FactsInfoPanel("System", id="facts-system-info")

                # Config Info Panel
                with FocusPanel("Configuration", id="facts-config-panel", classes="panel-orange"):
                    yield FactsInfoPanel("Config", id="facts-config-info")

            # Statistics Panel (bottom)
            with FocusPanel("Statistics", id="facts-stats-panel", classes="panel-orange"):
                yield FactsInfoPanel("Stats", id="facts-stats-info")

        # Facts footer
        yield FactsFooter()

    async def on_mount(self) -> None:
        """Initialize the Facts screen."""
        # Load data on mount
        await self._load_facts_data()

    async def _load_facts_data(self) -> None:
        """Load facts data from device manager and connection manager."""
        try:
            # Get device manager from app
            device_manager = getattr(self.app, 'device_manager', None)
            conn_mgr = getattr(self.app, 'conn_mgr', None)

            if not conn_mgr:
                return

            # Update sessions table
            sessions_table = self.query_one("#facts-sessions-table", DeviceSessionsTable)
            sessions_table.set_sessions(conn_mgr.sessions)

            # Update system info
            system_info = self._get_system_info(conn_mgr)
            system_panel = self.query_one("#facts-system-info", FactsInfoPanel)
            system_panel.set_data(system_info)

            # Update config info
            config_info = self._get_config_info()
            config_panel = self.query_one("#facts-config-info", FactsInfoPanel)
            config_panel.set_data(config_info)

            # Update stats
            stats = self._get_statistics(conn_mgr, device_manager)
            stats_panel = self.query_one("#facts-stats-info", FactsInfoPanel)
            stats_panel.set_data(stats)

            # Update header
            header = self.query_one("#facts-header", FactsHeader)
            header.update_last_poll()

        except Exception as e:
            # Show error
            pass

    def _get_system_info(self, conn_mgr) -> Dict[str, Any]:
        """Get system information."""
        info = {}

        # Connection info
        total_sessions = len(conn_mgr.sessions)
        connected = sum(1 for s in conn_mgr.sessions.values()
                       if hasattr(s, 'state') and s.state.value == "CONNECTED")
        failed = sum(1 for s in conn_mgr.sessions.values()
                    if hasattr(s, 'state') and s.state.value == "FAILED")

        info["Sessions"] = {
            "Total": total_sessions,
            "Connected": connected,
            "Failed": failed,
        }

        # App info
        app = self.app
        info["Application"] = {
            "Name": "Pulse",
            "WebSocket": "ONLINE" if getattr(app, 'ws_connected', False) else "OFFLINE",
            "Backend": "READY" if getattr(app, 'backend_ready', False) else "NOT READY",
        }

        return info

    def _get_config_info(self) -> Dict[str, Any]:
        """Get configuration information."""
        config = getattr(self.app, 'config', None)

        if not config:
            return {"Status": "Configuration not available"}

        return {
            "Polling Interval": f"{config.polling_interval}s",
            "Connection Timeout": f"{config.connection_timeout}s",
            "Retry Attempts": str(config.retry_attempts),
            "Cache TTL": f"{config.cache_ttl}s",
        }

    def _get_statistics(self, conn_mgr, device_manager) -> Dict[str, Any]:
        """Get statistics from device manager."""
        if not device_manager:
            return {"Status": "Device manager not available"}

        polling_stats = device_manager.get_polling_stats()
        device_counts = device_manager.get_device_counts()

        stats = {
            "Devices": {
                "Total": device_counts.get("total", 0),
                "Connected": device_counts.get("connected", 0),
                "Failed": device_counts.get("failed", 0),
            },
            "Polling": {
                "Total Polls": polling_stats.get("total_polls", 0),
                "Successful": polling_stats.get("successful_polls", 0),
                "Failed": polling_stats.get("failed_polls", 0),
                "Interval": polling_stats.get("interval", "MANUAL"),
            },
        }

        if polling_stats.get("last_poll"):
            stats["Last Poll"] = polling_stats["last_poll"]

        return stats

    def on_key(self, event) -> None:
        """Handle key events at screen level for panel navigation."""
        if event.key == "tab":
            self.action_cycle_panels()
            event.stop()

    def action_cycle_panels(self) -> None:
        """Cycle focus through panels."""
        panels = [
            "#facts-sessions-panel",
            "#facts-system-panel",
            "#facts-config-panel",
            "#facts-stats-panel"
        ]

        # Find currently focused panel
        current_focused = self.focused

        if current_focused:
            # Check if current focus is in a panel
            current_panel = current_focused
            while current_panel and not isinstance(current_panel, FocusPanel):
                current_panel = current_panel.parent

            # Find the index of the current panel
            try:
                current_index = -1
                for i, panel_id in enumerate(panels):
                    try:
                        panel = self.query_one(panel_id)
                        if panel == current_panel:
                            current_index = i
                            break
                    except Exception:
                        continue

                # Focus the next panel
                if current_index >= 0:
                    next_index = (current_index + 1) % len(panels)
                    next_panel = self.query_one(panels[next_index], FocusPanel)
                    next_panel.focus()
            except Exception:
                # If we can't determine current panel, focus the first one
                try:
                    first_panel = self.query_one(panels[0], FocusPanel)
                    first_panel.focus()
                except Exception:
                    pass
        else:
            # Nothing focused, focus the first panel
            try:
                first_panel = self.query_one(panels[0], FocusPanel)
                first_panel.focus()
            except Exception:
                pass

    def action_refresh(self) -> None:
        """Refresh facts data."""
        asyncio.create_task(self._load_facts_data())

    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
