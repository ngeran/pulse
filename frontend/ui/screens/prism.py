"""
prism.py
────────
PRISM - Probe-based Real-time Infrastructure & Service Monitor

Real-time Juniper RPM monitoring dashboard with:
- Live probe status table
- Historical sparkline graphs
- Alert log
- Summary metrics
"""

from typing import Optional, Dict, List, Any
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, Header, Footer
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from pathlib import Path
from rich.text import Text
from datetime import datetime
import time

# Import modular header and footer
from frontend.ui.widgets.prism_header import PrismHeader
from frontend.ui.widgets.prism_footer import PrismFooter

# Import focusable panel system
from frontend.ui.widgets.focus_panel import FocusPanel, FocusableStatic


class PrismMetricCard(FocusableStatic):
    """A metric summary card."""

    def __init__(self, label: str, value: str, color: str = "#faf9f5", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.color = color

    def update_content(self) -> None:
        """Update the card content."""
        text = Text()
        text.append(f"{self.label}\n", style="#c2c0b6")
        text.append(f"{self.value}", style=f"bold {self.color}")
        self.update(text)

    def on_mount(self) -> None:
        """Initialize content."""
        self.update_content()

    def set_value(self, value: str, color: Optional[str] = None) -> None:
        """Update the value and optional color."""
        self.value = value
        if color:
            self.color = color
        self.update_content()


class PrismProbeTable(FocusableStatic):
    """Table displaying probe results with keyboard navigation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.probes = []
        self.selected_index = 0
        self._history_panel = None

    def on_mount(self) -> None:
        """Initialize table with sample data."""
        self._load_sample_data()
        self._render_table()

    def set_history_panel(self, panel) -> None:
        """Set the history panel to update on selection change."""
        self._history_panel = panel

    def _load_sample_data(self) -> None:
        """Load sample probe data."""
        self.probes = [
            {
                "owner": "router-a",
                "target": "8.8.8.8",
                "latency": 10.2,
                "jitter": 0.9,
                "loss": 0.0,
                "status": "OK"
            },
            {
                "owner": "router-a",
                "target": "1.1.1.1",
                "latency": 11.7,
                "jitter": 1.2,
                "loss": 0.0,
                "status": "OK"
            },
            {
                "owner": "router-b",
                "target": "10.0.0.1",
                "latency": 34.8,
                "jitter": 8.2,
                "loss": 1.0,
                "status": "WARN"
            },
            {
                "owner": "router-b",
                "target": "172.16.0.10",
                "latency": 198.3,
                "jitter": 44.1,
                "loss": 3.1,
                "status": "CRIT"
            },
            {
                "owner": "router-c",
                "target": "192.168.1.1",
                "latency": 5.4,
                "jitter": 0.6,
                "loss": 0.0,
                "status": "OK"
            },
        ]

    def _render_table(self) -> None:
        """Render the probe table with full-width columns."""
        text = Text()

        # Column widths (proportional to fill full width)
        # Increased to better fill the available panel space
        col_owner = 16      # Owner hostname
        col_target = 22     # Target IP/hostname
        col_latency = 13    # Latency value + unit
        col_jitter = 13     # Jitter value + unit
        col_loss = 11       # Loss percentage
        col_status = 9      # Status text

        # Header row
        text.append(f"{'Owner':<{col_owner}}", style="#c2c0b6")
        text.append(f"{'Target':<{col_target}}", style="#c2c0b6")
        text.append(f"{'Latency':<{col_latency}}", style="#c2c0b6")
        text.append(f"{'Jitter':<{col_jitter}}", style="#c2c0b6")
        text.append(f"{'Loss':<{col_loss}}", style="#c2c0b6")
        text.append(f"{'Status':<{col_status}}", style="#c2c0b6")
        text.append("\n")

        # Separator line
        total_width = col_owner + col_target + col_latency + col_jitter + col_loss + col_status
        text.append("─" * total_width + "\n", style="dim")

        # Data rows
        for idx, probe in enumerate(self.probes[:10]):  # Show first 10
            # Determine colors based on status
            if probe["status"] == "OK":
                loss_color = status_color = "#639922"
            elif probe["status"] == "WARN":
                loss_color = status_color = "#EF9F27"
            else:  # CRIT
                loss_color = status_color = "#E24B4A"

            # Row indicator and Owner
            if idx == self.selected_index:
                # Selected row - show "> " prefix
                text.append(f"> {(idx + 1)}. {probe['owner']:<{col_owner - 4}}", style="bold #00d7ff")
            else:
                # Normal row - show number prefix
                text.append(f"  {(idx + 1)}. {probe['owner']:<{col_owner - 4}}", style="#c2c0b6")

            # Target
            text.append(f"{probe['target']:<{col_target}}", style="#c2c0b6")

            # Latency (right-aligned within column)
            latency_str = f"{probe['latency']:.1f} ms"
            text.append(f"{latency_str:>{col_latency}}", style="#c2c0b6")

            # Jitter (right-aligned within column)
            jitter_str = f"{probe['jitter']:.1f} ms"
            text.append(f"{jitter_str:>{col_jitter}}", style="#c2c0b6")

            # Loss (right-aligned within column)
            loss_str = f"{probe['loss']:.1f} %"
            text.append(f"{loss_str:>{col_loss}}", style=loss_color)

            # Status (right-aligned within column)
            text.append(f"{probe['status']:>{col_status}}", style=status_color)

            text.append("\n")

        if len(self.probes) > 10:
            text.append(f"\n··· {len(self.probes) - 10} more probes ···", style="dim")

        self.update(text)

    def on_key(self, event) -> None:
        """Handle keyboard navigation."""
        if event.key == "up":
            self.cursor_up()
            event.stop()
        elif event.key == "down":
            self.cursor_down()
            event.stop()
        elif event.key == "enter":
            self.show_details()
            event.stop()

    def cursor_up(self) -> None:
        """Move selection up."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._render_table()
            self._update_history()

    def cursor_down(self) -> None:
        """Move selection down."""
        if self.selected_index < len(self.probes) - 1:
            self.selected_index += 1
            self._render_table()
            self._update_history()

    def show_details(self) -> None:
        """Show details for the selected probe."""
        probe = self.get_selected_probe()
        if probe:
            self._update_history()
            # Could open a detailed view modal here in the future
            self.notify(f"Selected: {probe['owner']} → {probe['target']}", severity="information")

    def _update_history(self) -> None:
        """Update the history panel with the selected probe."""
        if self._history_panel:
            probe = self.get_selected_probe()
            if probe:
                self._history_panel.set_probe(probe)

    def get_selected_probe(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected probe."""
        if 0 <= self.selected_index < len(self.probes):
            return self.probes[self.selected_index]
        return None


class PrismHistoryPanel(FocusableStatic):
    """Panel showing history sparklines for selected probe."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_probe = None

    def on_mount(self) -> None:
        """Initialize history panel."""
        self._render_history()

    def set_probe(self, probe: Dict[str, Any]) -> None:
        """Set the probe to display history for."""
        self.selected_probe = probe
        self._render_history()

    def _render_history(self) -> None:
        """Render the history panel."""
        text = Text()

        if not self.selected_probe:
            text.append("No probe selected", style="dim")
            self.update(text)
            return

        # Title
        owner = self.selected_probe.get("owner", "unknown")
        target = self.selected_probe.get("target", "unknown")
        text.append(f"History · {owner} → {target}\n\n", style="#c2c0b6")

        # Latency sparkline
        text.append("Latency (5 min)\n", style="dim")
        text.append("⣀⣀⣤⣤⣶⣶⣿⣿⣷⣾\n", style="#EF9F27")

        # Jitter sparkline
        text.append("\nJitter (5 min)\n", style="dim")
        text.append("⣀⣀⣠⣤⣦⣴⣶⣶⣿⣿\n", style="#E24B4A")

        # Loss sparkline
        text.append("\nLoss (5 min)\n", style="dim")
        text.append("⣀⣀⣀⣀⣤⣦⣶⣿⣿⣿\n", style="#E24B4A")

        self.update(text)


class PrismAlertLog(FocusableStatic):
    """Alert log panel showing recent alerts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alerts = []

    def on_mount(self) -> None:
        """Initialize with sample alerts."""
        self._load_sample_alerts()
        self._render_log()

    def _load_sample_alerts(self) -> None:
        """Load sample alerts."""
        self.alerts = [
            {
                "level": "CRIT",
                "time": datetime.now().replace(second=1, microsecond=0),
                "owner": "router-b",
                "target": "172.16.0.10",
                "latency": 198,
                "jitter": 44,
                "loss": 3.1
            },
            {
                "level": "WARN",
                "time": datetime.now().replace(second=47, microsecond=0),
                "owner": "router-b",
                "target": "10.0.0.1",
                "latency": 34,
                "jitter": 8,
                "loss": 1.0
            },
            {
                "level": "OK",
                "time": datetime.now().replace(minute=20, second=33, microsecond=0),
                "owner": "router-a",
                "target": "8.8.8.8",
                "latency": 10,
                "jitter": 0,
                "loss": 0.0,
                "recovered": True
            },
        ]

    def _render_log(self) -> None:
        """Render the alert log."""
        text = Text()

        for alert in self.alerts:
            level = alert["level"]
            timestamp = alert["time"].strftime("%H:%M:%S")

            # Color based on level
            if level == "CRIT":
                color = "#E24B4A"
            elif level == "WARN":
                color = "#EF9F27"
            else:
                color = "#639922"

            # Format alert message
            if alert.get("recovered"):
                msg = f"[{level:4}] {timestamp} {alert['owner']} → {alert['target']:<15} recovered  latency={alert['latency']}ms"
            else:
                msg = (f"[{level:4}] {timestamp} {alert['owner']} → {alert['target']:<15} "
                      f"latency={alert['latency']}ms  jitter={alert['jitter']}ms  loss={alert['loss']}%")

            text.append(msg + "\n", style=color)

        self.update(text)

    def add_alert(self, level: str, owner: str, target: str, **metrics) -> None:
        """Add a new alert to the log."""
        alert = {
            "level": level,
            "time": datetime.now(),
            "owner": owner,
            "target": target,
            **metrics
        }
        self.alerts.insert(0, alert)
        # Keep only last 50 alerts
        self.alerts = self.alerts[:50]
        self._render_log()


class PrismScreen(Screen):
    """PRISM - Probe-based Real-time Infrastructure & Service Monitor."""

    # Use CSS_PATH for live reloading in --dev mode
    CSS_PATH = Path(__file__).parent.parent / "styles" / "prism.tcss"

    BINDINGS = [
        ("b", "back", "Back to Dashboard"),
        ("q", "quit", "Quit Application"),
        ("r", "refresh", "Refresh Probes"),
        ("tab", "cycle_panels", "Cycle Panels"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the PRISM screen."""
        # Modular PRISM header (includes status info)
        yield PrismHeader("PRISM", id="prism-header")

        with Vertical(id="prism-container"):
            # Metric cards row - wrapped in FocusPanel
            with FocusPanel("Metrics", id="prism-metrics-panel", classes="panel-orange"):
                with Horizontal(id="prism-metrics"):
                    yield PrismMetricCard("Avg latency", "12.4 ms", id="metric-latency")
                    yield PrismMetricCard("Avg jitter", "1.8 ms", id="metric-jitter")
                    yield PrismMetricCard("Packet loss", "3.1 %", "#E24B4A", id="metric-loss")
                    yield PrismMetricCard("Alerts active", "2", "#EF9F27", id="metric-alerts")

            # Main content row
            with Horizontal(id="prism-main"):
                # Probe table (left, larger) - wrapped in FocusPanel
                with FocusPanel("Probe Table", id="prism-probe-panel", classes="panel-orange"):
                    yield PrismProbeTable(id="prism-probe-table")

                # History panel (right, smaller) - wrapped in FocusPanel
                with FocusPanel("History", id="prism-history-panel", classes="panel-orange"):
                    yield PrismHistoryPanel(id="prism-history")

            # Alert log (bottom, full width) - wrapped in FocusPanel
            with FocusPanel("Alert Log", id="prism-alert-log-panel", classes="panel-orange"):
                yield PrismAlertLog(id="prism-alert-log")

        # Modular footer
        yield PrismFooter()

    async def on_mount(self) -> None:
        """Initialize the PRISM screen."""
        # Update header with sample stats
        try:
            header = self.query_one("#prism-header", PrismHeader)
            header.set_probe_stats(devices=3, probes=24, interval=5)
            header.update_last_poll()
        except Exception:
            pass

        # Link probe table selection to history panel
        try:
            probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
            history_panel = self.query_one("#prism-history", PrismHistoryPanel)
            # Set the history panel reference for automatic updates
            probe_table.set_history_panel(history_panel)
            # Initialize with first selection
            selected_probe = probe_table.get_selected_probe()
            if selected_probe:
                history_panel.set_probe(selected_probe)
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key events at screen level for panel navigation."""
        if event.key == "tab":
            self.action_cycle_panels()
            event.stop()

    def action_cycle_panels(self) -> None:
        """Cycle focus through panels."""
        panels = [
            "#prism-metrics-panel",
            "#prism-probe-panel",
            "#prism-history-panel",
            "#prism-alert-log-panel"
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
        """Refresh probe data."""
        # This would trigger actual probe refresh from backend
        try:
            probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
            probe_table._render_table()
        except Exception:
            pass

    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
