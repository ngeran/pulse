"""
prism.py
────────
PRISM - Probe-based Real-time Infrastructure & Service Monitor

Real-time Juniper RPM monitoring dashboard with:
- Device selector
- Probe table with max/min/avg statistics
- Detailed probe information
- TWAMP data panel
"""

from typing import Optional, Dict, List, Any
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from pathlib import Path
from rich.text import Text
from datetime import datetime
import asyncio

# Import modular header and footer
from frontend.ui.widgets.prism_header import PrismHeader
from frontend.ui.widgets.prism_footer import PrismFooter

# Import focusable panel system
from frontend.ui.widgets.focus_panel import FocusPanel, FocusableStatic

# Import TWAMP engine
from backend.core.twamp_engine import TWAMPEngine, TWAMPMetrics


class PrismDeviceSelector(FocusableStatic):
    """Device selector for PRISM screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.devices = []
        self.selected_device = None  # None means "All Devices"

    def set_devices(self, devices: List[str]) -> None:
        """Set the list of connected devices."""
        self.devices = ["All Devices"] + list(devices)
        self._render_selector()

    def set_selected_device(self, device: Optional[str]) -> None:
        """Set the selected device (None for All)."""
        self.selected_device = device
        self._render_selector()

    def _render_selector(self) -> None:
        """Render the device selector."""
        text = Text()

        if not self.devices:
            text.append("No devices connected - Connect devices in Device Management", style="dim #888888")
        else:
            for idx, device in enumerate(self.devices):
                # Check if this device is selected
                is_selected = (device == "All Devices" and self.selected_device is None) or \
                             (device == self.selected_device)

                if is_selected:
                    # Highlight selected device
                    if device == "All Devices":
                        text.append("[*ALL*] ", style="bold #ff8800 on #3a2a00")
                    else:
                        text.append(f"[*{device}*] ", style="bold #ff8800 on #3a2a00")
                else:
                    # Show device name
                    if device == "All Devices":
                        text.append("[ALL] ", style="#00d7ff")
                    else:
                        text.append(f"[{device}] ", style="dim #00d7ff")

            text.append("\n", style="")
            text.append("Use left/right arrows to select device", style="dim #888888")

        self.update(text)

    def get_selected_device(self) -> Optional[str]:
        """Get the currently selected device name (None for All)."""
        return self.selected_device

    def cycle_devices(self, forward: bool = True) -> None:
        """Cycle through devices."""
        if not self.devices:
            return

        # Find current index
        if self.selected_device is None:
            current_idx = 0  # "All Devices"
        else:
            try:
                current_idx = self.devices.index(self.selected_device)
            except ValueError:
                current_idx = 0

        # Calculate next index
        if forward:
            next_idx = (current_idx + 1) % len(self.devices)
        else:
            next_idx = (current_idx - 1) % len(self.devices)

        # Update selected device
        if next_idx == 0:
            self.selected_device = None  # "All Devices"
        else:
            self.selected_device = self.devices[next_idx]

        self._render_selector()


class PrismProbeTable(FocusableStatic):
    """Table displaying TWAMP probe results with statistics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.probes = []
        self.selected_index = 0
        self._details_panel = None

    def on_mount(self) -> None:
        """Initialize table."""
        self._render_empty()

    def set_details_panel(self, panel) -> None:
        """Set the details panel to update on selection change."""
        self._details_panel = panel

    def _render_empty(self) -> None:
        """Render empty state."""
        text = Text()
        text.append("No TWAMP data available.\n", style="dim #c2c0b6")
        text.append("Connect devices and ensure polling is enabled.\n", style="dim #c2c0b6")
        self.update(text)

    def load_probes(self, metrics_list: List[TWAMPMetrics]) -> None:
        """Load probe data from TWAMP metrics."""
        self.probes = []

        for metrics in metrics_list:
            probe = {
                "owner": metrics.owner,
                "test_name": metrics.test_name,
                "target": metrics.reflector_address,
                "latency_avg_ms": metrics.avg_latency_usec / 1000.0,
                "latency_min_ms": metrics.min_latency_usec / 1000.0,
                "latency_max_ms": metrics.max_latency_usec / 1000.0,
                "jitter_avg_ms": metrics.jitter_usec / 1000.0,
                "loss_pct": metrics.loss_percentage,
                "status": metrics.status,
                "probes_sent": metrics.probes_sent,
                "probes_received": metrics.probes_received,
            }
            self.probes.append(probe)

        self._render_table()

    def _render_table(self) -> None:
        """Render the probe table."""
        text = Text()

        # Column widths
        col_owner = 18
        col_latency = 22
        col_jitter = 15
        col_loss = 12
        col_status = 9

        # Header row
        text.append(f"{'Owner/Test':<{col_owner}}", style="#c2c0b6")
        text.append(f"{'Latency (ms)':<{col_latency}}", style="#c2c0b6")
        text.append(f"{'Jitter (ms)':<{col_jitter}}", style="#c2c0b6")
        text.append(f"{'Loss %':<{col_loss}}", style="#c2c0b6")
        text.append(f"{'Status':<{col_status}}", style="#c2c0b6")
        text.append("\n")

        # Separator line
        total_width = col_owner + col_latency + col_jitter + col_loss + col_status
        text.append("─" * total_width + "\n", style="dim")

        # Data rows
        for idx, probe in enumerate(self.probes[:15]):  # Show first 15
            # Determine colors based on status
            if probe["status"] == "OK":
                status_color = "#639922"
            elif probe["status"] == "WARN":
                status_color = "#EF9F27"
            else:  # CRIT
                status_color = "#E24B4A"

            # Row indicator and Owner/Test
            if idx == self.selected_index:
                text.append(f"> ", style="bold #00d7ff")
            else:
                text.append("  ", style="")

            # Owner and test name
            owner_str = f"{probe['owner']}/{probe['test_name']}"
            text.append(f"{owner_str:<{col_owner - 2}}", style="#c2c0b6")

            # Latency (min/avg/max)
            latency_str = f"{probe['latency_min_ms']:.1f}/{probe['latency_avg_ms']:.1f}/{probe['latency_max_ms']:.1f}"
            text.append(f"{latency_str:>{col_latency}}", style="#c2c0b6")

            # Jitter (avg)
            jitter_str = f"{probe['jitter_avg_ms']:.2f}"
            text.append(f"{jitter_str:>{col_jitter}}", style="#c2c0b6")

            # Loss
            loss_str = f"{probe['loss_pct']:.2f}"
            text.append(f"{loss_str:>{col_loss}}", style=status_color)

            # Status
            text.append(f"{probe['status']:>{col_status}}", style=status_color)

            text.append("\n")

        if len(self.probes) > 15:
            text.append(f"\n··· {len(self.probes) - 15} more probes ···", style="dim")

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
            self._update_details()

    def cursor_down(self) -> None:
        """Move selection down."""
        if self.selected_index < len(self.probes) - 1:
            self.selected_index += 1
            self._render_table()
            self._update_details()

    def show_details(self) -> None:
        """Show details for selected probe."""
        self._update_details()

    def _update_details(self) -> None:
        """Update the details panel."""
        if self._details_panel and self.probes:
            self._details_panel.set_probe(self.probes[self.selected_index])

    def get_selected_probe(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected probe."""
        if self.probes and self.selected_index < len(self.probes):
            return self.probes[self.selected_index]
        return None


class PrismDetailsPanel(FocusableStatic):
    """Panel showing detailed information about the selected probe."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.probe = None

    def set_probe(self, probe: dict) -> None:
        """Set the probe to display details for."""
        self.probe = probe
        self._render_details()

    def _render_details(self) -> None:
        """Render the details panel."""
        text = Text()

        if not self.probe:
            text.append("Select a probe to view details.", style="dim #c2c0b6")
            self.update(text)
            return

        # Header
        text.append(f"{self.probe.get('test_name', 'N/A')}\n", style="bold #00d7ff")
        text.append("─" * 40 + "\n\n", style="dim")

        # Session info
        text.append("[Session]\n", style="bold #c2c0b6")
        text.append(f"Owner:     {self.probe.get('owner', 'N/A')}\n", style="#c2c0b6")
        text.append(f"Reflector: {self.probe.get('target', 'N/A')}\n\n", style="#c2c0b6")

        # Latency stats
        text.append("[Latency (ms)]\n", style="bold #c2c0b6")
        if 'latency_min_ms' in self.probe:
            text.append(f"Min: {self.probe['latency_min_ms']:.1f}\n", style="#c2c0b6")
            text.append(f"Max: {self.probe['latency_max_ms']:.1f}\n", style="#c2c0b6")
        text.append(f"Avg: {self.probe.get('latency_avg_ms', 0):.1f}\n\n", style="#c2c0b6")

        # Jitter stats
        text.append("[Jitter (ms)]\n", style="bold #c2c0b6")
        text.append(f"Avg: {self.probe.get('jitter_avg_ms', 0):.2f}\n\n", style="#c2c0b6")

        # Packet loss
        text.append("[Packet Loss]\n", style="bold #c2c0b6")
        loss = self.probe.get('loss_pct', 0)
        text.append(f"Loss: {loss:.2f}%\n\n", style=self._get_loss_color(loss))

        # Probe counts
        if 'probes_sent' in self.probe:
            text.append("[Probes]\n", style="bold #c2c0b6")
            text.append(f"Sent:     {self.probe['probes_sent']}\n", style="#c2c0b6")
            text.append(f"Received: {self.probe['probes_received']}\n", style="#c2c0b6")

        # Status
        text.append(f"\nStatus: {self.probe.get('status', 'UNKNOWN')}", style=self._get_status_color(self.probe.get('status', 'UNKNOWN')))

        self.update(text)

    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        if status == "OK":
            return "#639922"
        elif status == "WARN":
            return "#EF9F27"
        else:  # CRIT
            return "#E24B4A"

    def _get_loss_color(self, loss: float) -> str:
        """Get color for packet loss percentage."""
        if loss >= 1.0:
            return "#E24B4A"
        elif loss >= 0.5:
            return "#EF9F27"
        else:
            return "#639922"


class PrismTWAMPPanel(FocusableStatic):
    """Panel displaying TWAMP data per device."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.twamp_data = {}

    def set_twamp_data(self, twamp_data: Dict[str, List[TWAMPMetrics]]) -> None:
        """Set the TWAMP data to display."""
        self.twamp_data = twamp_data
        print(f"[DEBUG] PrismTWAMPPanel received data: {list(twamp_data.keys())}")
        for device, metrics in twamp_data.items():
            print(f"[DEBUG]   {device}: {len(metrics)} metrics")
        self._render_twamp()

    def _render_twamp(self) -> None:
        """Render the TWAMP data panel."""
        print("[DEBUG] _render_twamp called")
        text = Text()

        if not self.twamp_data:
            text.append("No TWAMP data available.\n", style="dim #c2c0b6")
            text.append("Connect devices and enable polling to see TWAMP data.", style="dim #c2c0b6")
            self.update(text)
            return

        print(f"[DEBUG] Rendering {len(self.twamp_data)} devices")
        # Display data by device
        for device_name, metrics_list in self.twamp_data.items():
            print(f"[DEBUG] Rendering device: {device_name} with {len(metrics_list)} metrics")
            if not metrics_list:
                continue

            # Device header
            text.append(f"\n{device_name}\n", style="bold #00d7ff")
            text.append("─" * 40 + "\n", style="dim")

            # Display each probe/test
            for metrics in metrics_list:
                text.append(f"\n  Test: {metrics.test_name}\n", style="bold #c2c0b6")
                text.append(f"  Target: {metrics.reflector_address}:{metrics.reflector_port}\n", style="#c2c0b6")
                text.append(f"  Sender: {metrics.sender_address}:{metrics.sender_port}\n", style="#c2c0b6")

                # Statistics
                text.append(f"\n  Latency: {metrics.avg_latency_usec / 1000.0:.1f} ms", style="#c2c0b6")
                text.append(f" (min: {metrics.min_latency_usec / 1000.0:.1f}, max: {metrics.max_latency_usec / 1000.0:.1f})\n", style="dim")
                text.append(f"  Jitter: {metrics.jitter_usec / 1000.0:.2f} ms\n", style="#c2c0b6")
                text.append(f"  Loss: {metrics.loss_percentage:.2f}%\n", style=self._get_loss_color(metrics.loss_percentage))
                text.append(f"  Status: {metrics.status}\n", style=self._get_status_color(metrics.status))

                # Probe counts
                text.append(f"  Probes: {metrics.probes_received}/{metrics.probes_sent} received\n", style="#c2c0b6")

        print(f"[DEBUG] Updating TWAMP panel")
        self.update(text)

    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        if status == "OK":
            return "#639922"
        elif status == "WARN":
            return "#EF9F27"
        else:  # CRIT
            return "#E24B4A"

    def _get_loss_color(self, loss: float) -> str:
        """Get color for packet loss percentage."""
        if loss >= 1.0:
            return "#E24B4A"
        elif loss >= 0.5:
            return "#EF9F27"
        else:
            return "#639922"


class PrismScreen(Screen):
    """PRISM - Probe-based Real-time Infrastructure & Service Monitor."""

    # Use CSS_PATH for live reloading in --dev mode
    CSS_PATH = Path(__file__).parent.parent / "styles" / "prism.tcss"

    BINDINGS = [
        ("b", "back", "Back to Dashboard"),
        ("q", "quit", "Quit Application"),
        ("r", "refresh", "Refresh Probes"),
        ("tab", "cycle_panels", "Cycle Panels"),
        ("left", "prev_device", "Previous Device"),
        ("right", "next_device", "Next Device"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.twamp_engine = TWAMPEngine()
        self._all_metrics = []  # Store all TWAMP metrics
        self._polling_task = None

    def compose(self) -> ComposeResult:
        """Compose the PRISM screen."""
        # Modular PRISM header (includes status info)
        yield PrismHeader("PRISM", id="prism-header")

        with Vertical(id="prism-container"):
            # Device selector panel
            with FocusPanel("Device Selection", id="prism-device-panel", classes="panel-orange"):
                yield PrismDeviceSelector(id="prism-device-selector")

            # Main content area: Probe Table (left) and Details (right)
            with Horizontal(id="prism-main"):
                # Probe table (left, larger) - wrapped in FocusPanel
                with FocusPanel("Probe Table", id="prism-probe-panel", classes="panel-orange"):
                    yield PrismProbeTable(id="prism-probe-table")

                # Details panel (right, smaller) - wrapped in FocusPanel
                with FocusPanel("Details", id="prism-details-panel", classes="panel-orange"):
                    yield PrismDetailsPanel(id="prism-details")

            # TWAMP Data panel (bottom, full width) - wrapped in FocusPanel
            with FocusPanel("TWAMP Data", id="prism-twamp-panel", classes="panel-orange"):
                yield PrismTWAMPPanel(id="prism-twamp-data")

        # Modular footer
        yield PrismFooter()

    async def on_mount(self) -> None:
        """Initialize the PRISM screen."""
        # Link probe table selection to details panel
        try:
            probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
            details_panel = self.query_one("#prism-details", PrismDetailsPanel)
            probe_table.set_details_panel(details_panel)
        except Exception:
            pass

        # Populate device selector with connected devices
        await self._populate_device_selector()

        # Subscribe to TWAMP updates from device_manager
        device_manager = getattr(self.app, 'device_manager', None)
        if device_manager:
            device_manager.subscribe_to_twamp_updates(self._on_twamp_update)

        # Fetch real TWAMP data on mount
        await self._fetch_twamp_data()

    async def _populate_device_selector(self) -> None:
        """Populate the device selector with connected devices."""
        try:
            conn_mgr = getattr(self.app, 'conn_mgr', None)
            device_manager = getattr(self.app, 'device_manager', None)

            print(f"[DEBUG] _populate_device_selector: conn_mgr={conn_mgr}")
            if conn_mgr:
                print(f"[DEBUG] conn_mgr.sessions: {list(conn_mgr.sessions.keys())}")

            # Try to get devices from device_manager's twamp_data
            if device_manager:
                twamp_data = device_manager.get_twamp_data()
                print(f"[DEBUG] twamp_data keys: {list(twamp_data.keys())}")
                # Get unique device names from TWAMP data owner field
                devices_from_twamp = set()
                for device_name, metrics_list in twamp_data.items():
                    devices_from_twamp.add(device_name)

                connected_devices = list(devices_from_twamp)
                print(f"[DEBUG] Devices from TWAMP: {connected_devices}")

            # Also check conn_mgr.sessions for connected devices
            if conn_mgr:
                session_devices = [
                    host for host, session in conn_mgr.sessions.items()
                    if hasattr(session, 'state') and session.state.value == "CONNECTED"
                ]
                print(f"[DEBUG] Devices from conn_mgr: {session_devices}")

                # Combine both lists
                all_devices = list(set(connected_devices + session_devices))
            else:
                all_devices = list(devices_from_twamp) if devices_from_twamp else []

            print(f"[DEBUG] Total devices to show: {all_devices}")

            # Update device selector
            device_selector = self.query_one("#prism-device-selector", PrismDeviceSelector)
            device_selector.set_devices(all_devices)

        except Exception as e:
            print(f"[ERROR] _populate_device_selector error: {e}")
            import traceback
            traceback.print_exc()

    async def _fetch_twamp_data(self) -> None:
        """Fetch TWAMP data from device_manager and update UI."""
        print("[DEBUG] _fetch_twamp_data called")
        try:
            # Get device manager from app
            device_manager = getattr(self.app, 'device_manager', None)
            conn_mgr = getattr(self.app, 'conn_mgr', None)

            print(f"[DEBUG] device_manager: {device_manager}")
            print(f"[DEBUG] conn_mgr: {conn_mgr}")

            if not device_manager:
                print("[DEBUG] No device_manager")
                self._show_no_connection()
                return

            # Get selected device from selector
            device_selector = self.query_one("#prism-device-selector", PrismDeviceSelector)
            selected_device = device_selector.get_selected_device()
            print(f"[DEBUG] selected_device: {selected_device}")

            # Get TWAMP data from device_manager (it's already fetched during polling)
            twamp_data = device_manager.get_twamp_data()
            print(f"[DEBUG] twamp_data keys: {list(twamp_data.keys())}")

            # Populate device selector if empty
            if not device_selector.devices or (not device_selector.devices and twamp_data):
                devices_from_twamp = list(twamp_data.keys())
                device_selector.set_devices(devices_from_twamp)
                print(f"[DEBUG] Updated device selector with {len(devices_from_twamp)} devices")

            # Filter by selected device if specified
            if selected_device:
                twamp_data = {selected_device: twamp_data.get(selected_device, [])}
                print(f"[DEBUG] Filtered to device: {selected_device}")
            else:
                print(f"[DEBUG] Showing all devices")

            # Update TWAMP panel with raw data
            twamp_panel = self.query_one("#prism-twamp-data", PrismTWAMPPanel)
            twamp_panel.set_twamp_data(twamp_data)

            # Flatten metrics for probe table
            self._all_metrics = []
            total_probes = 0
            active_alerts = 0

            for device_name, metrics_list in twamp_data.items():
                print(f"[DEBUG] Device: {device_name}, Metrics: {len(metrics_list)}")
                self._all_metrics.extend(metrics_list)
                total_probes += len(metrics_list)

                # Count alerts (WARN and CRIT status)
                for metrics in metrics_list:
                    if metrics.status in ["WARN", "CRIT"]:
                        active_alerts += 1

            print(f"[DEBUG] Total metrics: {len(self._all_metrics)}, Total probes: {total_probes}")

            # Update probe table
            if self._all_metrics:
                probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
                probe_table.load_probes(self._all_metrics)

                # Update details panel with first probe
                if self._all_metrics:
                    probe_data = {
                        "owner": self._all_metrics[0].owner,
                        "test_name": self._all_metrics[0].test_name,
                        "target": self._all_metrics[0].reflector_address,
                        "latency_avg_ms": self._all_metrics[0].avg_latency_usec / 1000.0,
                        "latency_min_ms": self._all_metrics[0].min_latency_usec / 1000.0,
                        "latency_max_ms": self._all_metrics[0].max_latency_usec / 1000.0,
                        "jitter_avg_ms": self._all_metrics[0].jitter_usec / 1000.0,
                        "loss_pct": self._all_metrics[0].loss_percentage,
                        "status": self._all_metrics[0].status,
                        "probes_sent": self._all_metrics[0].probes_sent,
                        "probes_received": self._all_metrics[0].probes_received,
                    }
                    details_panel = self.query_one("#prism-details", PrismDetailsPanel)
                    details_panel.set_probe(probe_data)

                # Update header
                header = self.query_one("#prism-header", PrismHeader)

                # Get polling interval from device manager
                polling_interval_name = device_manager.polling_interval.name
                interval_seconds = device_manager.polling_interval.value
                print(f"[DEBUG] Polling interval: {polling_interval_name} ({interval_seconds}s)")

                # Get device count - use TWAMP data instead of conn_mgr sessions
                connected_count = len(twamp_data.keys())
                print(f"[DEBUG] Devices with TWAMP data: {connected_count}")

                header.set_probe_stats(
                    devices=connected_count,
                    probes=total_probes,
                    interval=interval_seconds if interval_seconds > 0 else 60
                )
                header.update_last_poll()
            else:
                print("[DEBUG] No metrics found, showing no data")
                self._show_no_data()

        except Exception as e:
            # Show error state
            print(f"[ERROR] _fetch_twamp_data error: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(str(e))

    async def _on_twamp_update(self, host: str, twamp_metrics: List[Any]) -> None:
        """Callback for TWAMP data updates from device_manager polling."""
        # Refresh the UI when new TWAMP data is available
        await self._fetch_twamp_data()

    def _show_no_connection(self) -> None:
        """Show no connection message."""
        try:
            probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
            probe_table._render_empty()
        except Exception:
            pass

    def _show_no_data(self) -> None:
        """Show no data message."""
        try:
            probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
            probe_table._render_empty()
        except Exception:
            pass

    def _show_error(self, error_msg: str) -> None:
        """Show error message."""
        try:
            probe_table = self.query_one("#prism-probe-table", PrismProbeTable)
            text = Text()
            text.append(f"Error fetching data:\n", style="#E24B4A")
            text.append(f"{error_msg}\n", style="dim #c2c0b6")
            probe_table.update(text)
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
            "#prism-device-panel",
            "#prism-probe-panel",
            "#prism-details-panel",
            "#prism-twamp-panel"
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
        asyncio.create_task(self._fetch_twamp_data())

    def action_prev_device(self) -> None:
        """Select previous device in list."""
        try:
            device_selector = self.query_one("#prism-device-selector", PrismDeviceSelector)
            device_selector.cycle_devices(forward=False)
            # Refresh data for new device
            asyncio.create_task(self._fetch_twamp_data())
        except Exception:
            pass

    def action_next_device(self) -> None:
        """Select next device in list."""
        try:
            device_selector = self.query_one("#prism-device-selector", PrismDeviceSelector)
            device_selector.cycle_devices(forward=True)
            # Refresh data for new device
            asyncio.create_task(self._fetch_twamp_data())
        except Exception:
            pass

    def action_back(self) -> None:
        """Go back to dashboard."""
        # Unsubscribe from TWAMP updates
        device_manager = getattr(self.app, 'device_manager', None)
        if device_manager:
            device_manager.unsubscribe_from_twamp_updates(self._on_twamp_update)

        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
