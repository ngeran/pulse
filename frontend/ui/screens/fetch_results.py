"""
Fetch Results Screen
────────────────────
Screen for displaying fetched data from a specific device.

Shows tabs for different data types (Facts, Interfaces, Routing, etc.)
"""

import asyncio
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Static, Header, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from pathlib import Path
from rich.text import Text
from backend.utils.logging import logger
from frontend.ui.widgets.fetch_results_footer import FetchResultsFooter
from frontend.ui.widgets.modular_header import ModularHeader


class FetchHeader(ModularHeader):
    """Header showing device name, last update time, and global status (WS, API)."""

    def __init__(self, **kwargs):
        super().__init__("FETCH RESULTS", **kwargs)
        self.device = None
        self.last_update = None

    def set_device(self, device: str) -> None:
        """Set the device name."""
        self.device = device
        self.update_status()

    def set_last_update(self, timestamp: str) -> None:
        """Set the last update timestamp."""
        self.last_update = timestamp
        self.update_status()

    def update_status(self) -> None:
        """Update the header content."""
        # First update global status (WS, API) from parent
        self._update_global_status()

        # Build global status fields (WS, API)
        if self._ws_status == "ONLINE":
            ws_field = "[#5aba5a on #2a4a2a] WS [/]"
        else:
            ws_field = "[#ba5a5a on #4a2a2a] WS [/]"

        if self._api_status == "ACTIVE":
            api_field = "[#5aba5a on #2a4a2a] API [/]"
        elif self._api_status == "INACTIVE":
            api_field = "[#ba8a5a on #4a3a2a] API [/]"
        else:  # DOWN
            api_field = "[#ba5a5a on #4a2a2a] API [/]"

        # Build fetch-specific fields
        if self.device:
            device_field = f"[#888888]Device:[/#5aba5a] {self.device}[/]"
        else:
            device_field = "[#888888]Device:[#888888] N/A[/]"

        if self.last_update:
            update_field = f"[#888888]Last Update:[#c2c0b6] {self.last_update}[/]"
        else:
            update_field = "[#888888]Last Update:[#888888] Never[/]"

        # Combine all fields: WS, API, Device info
        separator = " │ "
        status_content = separator.join([
            ws_field,
            api_field,
            device_field,
            update_field
        ])

        # Set status content using the base class method
        self._set_status_content(status_content)


class FetchDataView(Static):
    """Widget for displaying fetched data."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = None
        self.data_type = None

    def set_data(self, data_type: str, data: Dict[str, Any]) -> None:
        """Set the data to display."""
        self.data_type = data_type
        self.data = data
        self._render_data()

    def _render_data(self) -> None:
        """Render the data based on type."""
        if not self.data:
            self.update("No data available")
            return

        text = Text()

        if self.data.get("status") == "error":
            text.append(f"Error: {self.data.get('error', 'Unknown error')}", style="bold #ba5a5a")
            self.update(text)
            return

        data_content = self.data.get("data", {})
        timestamp = self.data.get('timestamp', 'N/A')

        # Header
        text.append(f"{self.data_type.upper()} | {timestamp}\n", style="dim")
        text.append("─────────────────────────────────────\n\n", style="dim")

        # Render based on data type
        if self.data_type == "facts":
            self._render_facts(text, data_content)
        elif self.data_type == "interfaces":
            self._render_interfaces(text, data_content)
        elif self.data_type == "routing":
            self._render_routing(text, data_content)
        elif self.data_type == "chassis":
            self._render_chassis(text, data_content)
        elif self.data_type == "ospf":
            self._render_ospf(text, data_content)
        elif self.data_type == "bgp":
            self._render_bgp(text, data_content)
        elif self.data_type == "ldp":
            self._render_ldp(text, data_content)
        elif self.data_type == "rsvp":
            self._render_rsvp(text, data_content)
        elif self.data_type == "optics":
            self._render_optics(text, data_content)
        elif self.data_type == "all":
            self._render_all(text, data_content)
        else:
            text.append("Unknown data type", style="#ba5a5a")

        self.update(text)

    def _render_facts(self, text: Text, data: Dict) -> None:
        """Render device facts."""
        for key, value in data.items():
            label = key.replace("_", " ").title()
            text.append(f"{label}: ", style="bold")
            text.append(f"{value}\n")

    def _render_interfaces(self, text: Text, data: Dict) -> None:
        """Render interface information."""
        interfaces = data.get("interfaces", [])
        text.append("Interface                Status       RX dBm    TX dBm    Errors\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for intf in interfaces[:20]:
            name = intf.get("name", "N/A")[:24].ljust(24)
            status = intf.get("oper_status", "unknown")[:12].ljust(12)
            rx = intf.get("rx_power_dbm", "N/A")[:9].ljust(9)
            tx = intf.get("tx_power_dbm", "N/A")[:9].ljust(9)
            errors = str(intf.get("errors", "0"))[:7]

            status_color = "#5aba5a" if status.strip().lower() == "up" else "#ba5a5a"
            text.append(f"{name}")
            text.append(f"{status}", style=status_color)
            text.append(f"{rx}{tx}{errors}\n")

        if len(interfaces) > 20:
            text.append(f"\n... and {len(interfaces) - 20} more", style="dim")

    def _render_routing(self, text: Text, data: Dict) -> None:
        """Render routing table."""
        routes = data.get("routes", [])
        text.append("Destination             Next Hop            Protocol  Age\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for route in routes[:25]:
            dest = route.get("destination", "N/A")[:21].ljust(21)
            nh = route.get("next_hop", "N/A")[:21].ljust(21)
            proto = route.get("protocol", "N/A")[:9].ljust(9)
            age = str(route.get("age_seconds", "0"))[:7]
            text.append(f"{dest}{nh}{proto}{age}\n")

        if len(routes) > 25:
            text.append(f"\n... and {len(routes) - 25} more", style="dim")

    def _render_chassis(self, text: Text, data: Dict) -> None:
        """Render chassis hardware info."""
        hardware = data.get("hardware", [])
        text.append("Type       Name                    Serial\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for item in hardware[:25]:
            itype = item.get("type", "N/A")[:11].ljust(11)
            name = item.get("name", "N/A")[:24].ljust(24)
            serial = item.get("serial", "N/A")[:20]
            text.append(f"{itype}{name}{serial}\n")

        if len(hardware) > 25:
            text.append(f"\n... and {len(hardware) - 25} more", style="dim")

    def _render_ospf(self, text: Text, data: Dict) -> None:
        """Render OSPF neighbors."""
        neighbors = data.get("neighbors", [])
        text.append("Interface            Neighbor ID          State\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for neighbor in neighbors:
            intf = neighbor.get("interface", "N/A")[:21].ljust(21)
            nid = neighbor.get("neighbor_id", "N/A")[:21].ljust(21)
            state = neighbor.get("state", "unknown")[:15]
            text.append(f"{intf}{nid}{state}\n")

    def _render_bgp(self, text: Text, data: Dict) -> None:
        """Render BGP peers."""
        peers = data.get("peers", [])
        text.append("Peer Address        AS           State               Flaps\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for peer in peers:
            addr = peer.get("peer_address", "N/A")[:21].ljust(21)
            asn = peer.get("peer_as", "N/A")[:13].ljust(13)
            state = peer.get("state", "unknown")[:20].ljust(20)
            flaps = str(peer.get("flap_count", "0"))[:7]
            text.append(f"{addr}{asn}{state}{flaps}\n")

    def _render_ldp(self, text: Text, data: Dict) -> None:
        """Render LDP neighbors."""
        neighbors = data.get("neighbors", [])
        text.append("Interface            Neighbor             State\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for neighbor in neighbors:
            intf = neighbor.get("interface", "N/A")[:21].ljust(21)
            nbr = neighbor.get("neighbor_address", "N/A")[:21].ljust(21)
            state = neighbor.get("state", "unknown")[:15]
            text.append(f"{intf}{nbr}{state}\n")

    def _render_rsvp(self, text: Text, data: Dict) -> None:
        """Render RSVP sessions."""
        sessions = data.get("sessions", [])
        text.append("Destination                      State\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for session in sessions:
            dest = session.get("destination", "N/A")[:33].ljust(33)
            state = session.get("lsp_state", "unknown")[:15]
            text.append(f"{dest}{state}\n")

    def _render_optics(self, text: Text, data: Dict) -> None:
        """Render optical diagnostics."""
        optics = data.get("optics", [])
        text.append("Interface            RX Power    TX Power    Temperature\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for optic in optics:
            intf = optic.get("interface", "N/A")[:21].ljust(21)
            rx = optic.get("rx_optical_power", "N/A")[:12].ljust(12)
            tx = optic.get("laser_output_power-dbm", "N/A")[:12].ljust(12)
            temp = optic.get("module_temperature", "N/A")[:12]
            text.append(f"{intf}{rx}{tx}{temp}\n")

    def _render_all(self, text: Text, data: Dict) -> None:
        """Render summary of all fetch results."""
        fetches = data.get("fetches", {})
        text.append("Type        Status           Count\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for fetch_type, result in fetches.items():
            ftype = fetch_type.upper()[:12].ljust(12)
            status = result.get("status", "unknown")[:16].ljust(16)

            count = "N/A"
            if result.get("status") == "success":
                result_data = result.get("data", {})
                if "count" in result_data:
                    count = str(result_data["count"])
                elif "interfaces" in result_data:
                    count = str(len(result_data["interfaces"]))
                elif "routes" in result_data:
                    count = str(len(result_data["routes"]))

            status_color = "#5aba5a" if result.get("status") == "success" else "#ba5a5a"
            text.append(ftype)
            text.append(status, style=status_color)
            text.append(f"{count}\n")


class FetchResultsScreen(Screen):
    """Screen for displaying fetched data from a specific device."""

    # Load stylesheets
    _CSS = Path(__file__).parent.parent / "styles" / "fetch_results.tcss"
    _MODULAR_FOOTER_CSS = Path(__file__).parent.parent / "styles" / "modular_footer.tcss"

    CSS = ""
    if _CSS.exists():
        CSS += _CSS.read_text()
    if _MODULAR_FOOTER_CSS.exists():
        CSS += _MODULAR_FOOTER_CSS.read_text()

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("b", "back", "Back to Device Management"),
        ("q", "back", "Back"),
        ("escape", "back", "Back"),
    ]

    def __init__(self, device: str, **kwargs):
        super().__init__(**kwargs)
        self.device = device
        self.api_base = "http://localhost:8001/api"
        self.current_tab = "facts"
        # Note: Don't use auto_refresh - it conflicts with Textual's automatic_refresh property
        self._polling_enabled = False
        self.refresh_interval = 60  # seconds
        self.refresh_task = None

    def compose(self) -> ComposeResult:
        """Compose the fetch results screen."""
        yield Header()

        with Vertical(id="fetch-results-container"):
            # Device header
            yield FetchHeader(id="fetch-header")

            # Tab buttons row
            with Horizontal(id="tab-buttons"):
                yield Button("Facts", id="btn-facts", variant="primary")
                yield Button("Interfaces", id="btn-interfaces")
                yield Button("Routing", id="btn-routing")
                yield Button("Chassis", id="btn-chassis")
                yield Button("OSPF", id="btn-ospf")
                yield Button("BGP", id="btn-bgp")
                yield Button("LDP", id="btn-ldp")
                yield Button("RSVP", id="btn-rsvp")
                yield Button("Optics", id="btn-optics")
                yield Button("ALL", id="btn-all")

            # Data view (current tab content)
            yield FetchDataView(id="fetch-data-view")

            # Instructions
            yield Static(
                "[r] Refresh  [b] Back  [q] Back  [1-9] Quick tab  [escape] Back",
                id="fetch-instructions"
            )

        # Modular footer with global and fetch-specific shortcuts
        yield FetchResultsFooter()

    async def on_mount(self) -> None:
        """Initialize the fetch results screen."""
        logger.info("fetch_results_mounted", device=self.device)

        # Set device in header
        header = self.query_one("#fetch-header", FetchHeader)
        header.set_device(self.device)

        # Load initial data (facts)
        await self._load_data(self.current_tab)

        # Highlight the first button
        self._update_tab_buttons()

    def on_unmount(self) -> None:
        """Clean up when screen is being removed."""
        logger.info("fetch_results_unmount", device=self.device)
        # Stop any running timers to prevent cleanup errors
        self._stop_all_timers()

    def _stop_all_timers(self) -> None:
        """Stop all timers safely."""
        try:
            # Access and stop timers through the app's timer mechanism
            if hasattr(self, '_timers') and self._timers:
                for timer_ref in list(self._timers):
                    try:
                        timer = timer_ref()
                        if timer and hasattr(timer, 'stop'):
                            timer.stop()
                    except Exception:
                        pass
                self._timers.clear()
        except Exception:
            pass

    def _update_tab_buttons(self) -> None:
        """Update tab button styles to show active tab."""
        button_map = {
            "facts": "btn-facts",
            "interfaces": "btn-interfaces",
            "routing": "btn-routing",
            "chassis": "btn-chassis",
            "ospf": "btn-ospf",
            "bgp": "btn-bgp",
            "ldp": "btn-ldp",
            "rsvp": "btn-rsvp",
            "optics": "btn-optics",
            "all": "btn-all",
        }

        active_button_id = button_map.get(self.current_tab)

        for data_type, btn_id in button_map.items():
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                if btn_id == active_button_id:
                    btn.variant = "primary"
                else:
                    btn.variant = "default"
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle tab button press."""
        button_id = event.button.id

        # Map button ID to data type
        button_map = {
            "btn-facts": "facts",
            "btn-interfaces": "interfaces",
            "btn-routing": "routing",
            "btn-chassis": "chassis",
            "btn-ospf": "ospf",
            "btn-bgp": "bgp",
            "btn-ldp": "ldp",
            "btn-rsvp": "rsvp",
            "btn-optics": "optics",
            "btn-all": "all",
        }

        new_tab = button_map.get(button_id)
        if new_tab and new_tab != self.current_tab:
            self.current_tab = new_tab
            self._update_tab_buttons()
            asyncio.create_task(self._load_data(self.current_tab))

    def on_key(self, event) -> None:
        """Handle key presses for quick tab navigation."""
        # Quick tab navigation with number keys
        if event.key in "123456789":
            key_map = {
                "1": "facts",
                "2": "interfaces",
                "3": "routing",
                "4": "chassis",
                "5": "ospf",
                "6": "bgp",
                "7": "ldp",
                "8": "rsvp",
                "9": "optics",
            }

            new_tab = key_map.get(event.key)
            if new_tab and new_tab != self.current_tab:
                self.current_tab = new_tab
                self._update_tab_buttons()
                asyncio.create_task(self._load_data(self.current_tab))
                event.stop()

    async def _load_data(self, data_type: str) -> None:
        """Load data from the backend API."""
        logger.info("fetch_results_loading", device=self.device, type=data_type)

        try:
            # Build URL
            if data_type == "all":
                url = f"{self.api_base}/devices/{self.device}/fetch/all"
            else:
                url = f"{self.api_base}/devices/{self.device}/fetch/{data_type}"

            # Use urllib in executor to avoid blocking
            loop = asyncio.get_event_loop()

            def fetch():
                try:
                    with urllib.request.urlopen(url, timeout=30) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        return response.status, data
                except urllib.error.HTTPError as e:
                    return e.code, {"error": str(e)}
                except Exception as e:
                    return 500, {"error": str(e)}

            status_code, data = await loop.run_in_executor(None, fetch)

            if status_code == 200:
                # Update the view
                view = self.query_one("#fetch-data-view", FetchDataView)
                view.set_data(data_type, data)

                # Update header timestamp
                header = self.query_one("#fetch-header", FetchHeader)
                header.set_last_update(data.get('timestamp', 'N/A'))

                logger.info("fetch_results_loaded", device=self.device, type=data_type, status="success")
            else:
                logger.error("fetch_results_failed", device=self.device, type=data_type, status=status_code)
                self.notify(f"Failed to load {data_type}: {data.get('error', 'Unknown error')}", severity="error")

        except Exception as e:
            logger.error("fetch_results_error", device=self.device, type=data_type, error=str(e))
            self.notify(f"Error loading {data_type}: {str(e)}", severity="error")

    def action_refresh(self) -> None:
        """Refresh the current tab's data."""
        logger.info("fetch_results_refresh", device=self.device, tab=self.current_tab)
        asyncio.create_task(self._load_data(self.current_tab))

    def action_back(self) -> None:
        """Go back to device management."""
        logger.info("fetch_results_back", device=self.device)
        self.app.pop_screen()
