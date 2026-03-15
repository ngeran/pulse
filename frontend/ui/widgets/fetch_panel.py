"""
fetch_panel.py
──────────────
Fetch panel widget that shows fetch options and displays results.

Matches the minimal aesthetic of PollingPanel with [x] bracket format
and simple > cursor navigation.
"""

import asyncio
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from textual.widgets import Static, DataTable
from textual.containers import Vertical
from textual.app import ComposeResult
from rich.text import Text
from backend.utils.logging import logger


class FetchContentStatic(Static):
    """Custom Static widget that forwards key events to FetchPanel."""

    def on_key(self, event) -> None:
        """Forward key events to parent FetchPanel and stop propagation."""
        logger.info("fetch_content_static_on_key", key=event.key, widget_id=self.id, focused=self.has_focus)
        print(f"[DEBUG FetchContentStatic] on_key: {event.key}, has_focus: {self.has_focus}")

        # Get parent FetchPanel and forward the key event
        parent = self.parent
        if parent and isinstance(parent, FetchPanel):
            logger.info("fetch_content_static_forwarding", parent_type=type(parent).__name__)
            print(f"[DEBUG FetchContentStatic] Forwarding to FetchPanel")
            parent.on_key(event)
            # Stop event from propagating further
            event.stop()
            event.prevent_default()
        else:
            logger.warning("fetch_content_static_no_parent", parent_type=type(parent).__name__ if parent else None)
            print(f"[DEBUG FetchContentStatic] No parent FetchPanel found")

    def _on_focus(self) -> None:
        """Called when widget receives focus."""
        logger.info("fetch_content_static_got_focus", widget_id=self.id)
        print(f"[DEBUG FetchContentStatic] Got focus!")
        super()._on_focus()


class FetchPanel(Vertical):
    """
    Fetch panel for displaying fetch options and results.

    Features:
    - Shows fetch options menu with [x] bracket format
    - Simple > cursor navigation (up/down arrows)
    - Displays fetch results in table format
    - Matches PollingPanel minimal aesthetic
    """

    # Make the panel focusable
    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_base = "http://localhost:8001/api"
        self.current_device: Optional[str] = None
        self.fetching = False
        self.current_data: Optional[Dict[str, Any]] = None
        self.current_fetch_type: Optional[str] = None
        self.cursor_index: int = 0  # For option selection
        self.showing_results = False
        self.is_active = False  # Track if fetch panel is active

        # Fetch options
        self.options = [
            ("1", "Facts"),
            ("2", "Interfaces"),
            ("3", "Routing"),
            ("4", "Chassis"),
            ("5", "OSPF"),
            ("6", "BGP"),
            ("7", "LDP"),
            ("8", "RSVP"),
            ("9", "Optics"),
            ("a", "ALL"),
        ]

    def compose(self) -> ComposeResult:
        """Compose the fetch panel layout."""
        yield FetchContentStatic(id="fetch-content")

    async def on_mount(self) -> None:
        """Initialize the fetch panel."""
        self._show_options()

    def _show_options(self) -> None:
        """Show fetch options menu with PollingPanel style."""
        self.current_device = None
        self.current_data = None
        self.current_fetch_type = None
        self.showing_results = False
        self.cursor_index = 0
        self.is_active = False

        content = self.query_one("#fetch-content", FetchContentStatic)
        self._update_options_display(content)

    def _update_options_display(self, content: FetchContentStatic) -> None:
        """Update the options display with cursor."""
        from rich.text import Text

        text = Text()

        if self.current_device:
            text.append(f"Device: ", style="bold")
            text.append(f"{self.current_device}\n", style="#5aba5a")
            text.append("─────────────────────────────────────\n\n", style="dim")
        else:
            text.append("─────────────────────────────────────\n\n", style="dim")

        # Show options with cursor indicator
        for idx, (key, name) in enumerate(self.options):
            is_selected = (idx == self.cursor_index)

            # Cursor indicator
            if is_selected:
                text.append("> ", style="#00d7ff")
            else:
                text.append("  ", style="#444444")

            # Colored bracket
            text.append(f"[{key}]", style="bold #00d7ff" if is_selected else "#444444")
            text.append(f" {name}\n")

        # Instructions at bottom
        text.append("\n─────────────────────────────────────\n\n", style="dim")
        text.append("[↑/↓]", style="bold #00d7ff")
        text.append(" Select option\n", style="dim")

        text.append("[Enter]", style="bold #00d7ff")
        text.append(" Fetch data\n", style="dim")

        text.append("[q]", style="bold #00d7ff")
        text.append(" Back to devices", style="dim")

        content.update(text)

    async def fetch_data(self, device_host: str, fetch_type: str) -> None:
        """Fetch data from backend API."""
        if self.fetching:
            return

        self.current_device = device_host
        self.fetching = True
        self.current_fetch_type = fetch_type

        # Show fetching message
        content = self.query_one("#fetch-content", FetchContentStatic)
        text = Text()
        text.append(f"Fetching {fetch_type}...\n", style="#6a8a8a")
        text.append(f"Device: {device_host}", style="dim")
        content.update(text)

        try:
            # Build URL
            if fetch_type == "all":
                url = f"{self.api_base}/devices/{device_host}/fetch/all"
            else:
                url = f"{self.api_base}/devices/{device_host}/fetch/{fetch_type}"

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
                self.current_data = data
                self.showing_results = True
                self._display_results()
                logger.info("fetch_success", device=device_host, type=fetch_type)
            else:
                self._show_error(f"HTTP {status_code}: {data.get('error', 'Unknown error')}")
                logger.error("fetch_failed", device=device_host, type=fetch_type, status=status_code)

        except urllib.error.URLError as e:
            self._show_error(f"Cannot connect to backend: {e.reason}")
            logger.error("fetch_url_error", device=device_host, type=fetch_type, error=str(e))
        except Exception as e:
            self._show_error(f"Fetch error: {str(e)}")
            logger.error("fetch_error", device=device_host, type=fetch_type, error=str(e))
        finally:
            self.fetching = False

    def _display_results(self) -> None:
        """Display fetched results."""
        if not self.current_data:
            self._show_error("No data to display")
            return

        content = self.query_one("#fetch-content", FetchContentStatic)
        text = Text()

        # Header with fetch type and timestamp
        text.append(f"{self.current_fetch_type.upper()} ", style="bold #5aba5a")
        timestamp = self.current_data.get('timestamp', 'N/A')
        text.append(f"| {timestamp}\n", style="dim")
        text.append("─────────────────────────────────────\n\n", style="dim")

        # Display data based on fetch type
        if self.current_data.get("status") == "error":
            text.append(f"Error: {self.current_data.get('error', 'Unknown error')}", style="#ba5a5a")
        elif self.current_fetch_type == "facts":
            self._display_facts(text)
        elif self.current_fetch_type == "interfaces":
            self._display_interfaces(text)
        elif self.current_fetch_type == "routing":
            self._display_routing(text)
        elif self.current_fetch_type == "chassis":
            self._display_chassis(text)
        elif self.current_fetch_type == "ospf":
            self._display_ospf(text)
        elif self.current_fetch_type == "bgp":
            self._display_bgp(text)
        elif self.current_fetch_type == "ldp":
            self._display_ldp(text)
        elif self.current_fetch_type == "rsvp":
            self._display_rsvp(text)
        elif self.current_fetch_type == "optics":
            self._display_optics(text)
        elif self.current_fetch_type == "all":
            self._display_all(text)

        # Instructions
        text.append("\n─────────────────────────────────────\n\n", style="dim")
        text.append("[q]", style="bold #00d7ff")
        text.append(" Back to options", style="dim")

        content.update(text)

    def _display_facts(self, text: Text) -> None:
        """Display device facts."""
        facts = self.current_data.get("data", {})
        for key, value in facts.items():
            label = key.replace("_", " ").title()
            text.append(f"{label}: ", style="bold")
            text.append(f"{value}\n")

    def _display_interfaces(self, text: Text) -> None:
        """Display interface information."""
        interfaces = self.current_data.get("data", {}).get("interfaces", [])
        text.append("Interface                Status       RX dBm    TX dBm    Errors\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for intf in interfaces[:15]:
            name = intf.get("name", "N/A")[:24].ljust(24)
            status = intf.get("oper_status", "unknown")[:12].ljust(12)
            rx = intf.get("rx_power_dbm", "N/A")[:9].ljust(9)
            tx = intf.get("tx_power_dbm", "N/A")[:9].ljust(9)
            errors = intf.get("errors", "0")[:7]

            # Color code status
            status_color = "#5aba5a" if status.strip().lower() == "up" else "#ba5a5a"

            text.append(f"{name}")
            text.append(f"{status}", style=status_color)
            text.append(f"{rx}")
            text.append(f"{tx}")
            text.append(f"{errors}\n")

        if len(interfaces) > 15:
            text.append(f"\n... and {len(interfaces) - 15} more", style="dim")

    def _display_routing(self, text: Text) -> None:
        """Display routing table."""
        routes = self.current_data.get("data", {}).get("routes", [])
        text.append("Destination             Next Hop            Protocol  Age\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for route in routes[:20]:
            dest = route.get("destination", "N/A")[:21].ljust(21)
            nh = route.get("next_hop", "N/A")[:21].ljust(21)
            proto = route.get("protocol", "N/A")[:9].ljust(9)
            age = route.get("age_seconds", "0")[:7]

            text.append(f"{dest}{nh}{proto}{age}\n")

        if len(routes) > 20:
            text.append(f"\n... and {len(routes) - 20} more", style="dim")

    def _display_chassis(self, text: Text) -> None:
        """Display chassis hardware info."""
        hardware = self.current_data.get("data", {}).get("hardware", [])
        text.append("Type       Name                    Serial\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for item in hardware[:20]:
            itype = item.get("type", "N/A")[:11].ljust(11)
            name = item.get("name", "N/A")[:24].ljust(24)
            serial = item.get("serial", "N/A")[:20]

            text.append(f"{itype}{name}{serial}\n")

        if len(hardware) > 20:
            text.append(f"\n... and {len(hardware) - 20} more", style="dim")

    def _display_ospf(self, text: Text) -> None:
        """Display OSPF neighbors."""
        neighbors = self.current_data.get("data", {}).get("neighbors", [])
        text.append("Interface            Neighbor ID          State\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for neighbor in neighbors:
            intf = neighbor.get("interface", "N/A")[:21].ljust(21)
            nid = neighbor.get("neighbor_id", "N/A")[:21].ljust(21)
            state = neighbor.get("state", "unknown")[:15]

            text.append(f"{intf}{nid}{state}\n")

    def _display_bgp(self, text: Text) -> None:
        """Display BGP peers."""
        peers = self.current_data.get("data", {}).get("peers", [])
        text.append("Peer Address        AS           State               Flaps\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for peer in peers:
            addr = peer.get("peer_address", "N/A")[:21].ljust(21)
            asn = peer.get("peer_as", "N/A")[:13].ljust(13)
            state = peer.get("state", "unknown")[:20].ljust(20)
            flaps = peer.get("flap_count", "0")[:7]

            text.append(f"{addr}{asn}{state}{flaps}\n")

    def _display_ldp(self, text: Text) -> None:
        """Display LDP neighbors."""
        neighbors = self.current_data.get("data", {}).get("neighbors", [])
        text.append("Interface            Neighbor             State\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for neighbor in neighbors:
            intf = neighbor.get("interface", "N/A")[:21].ljust(21)
            nbr = neighbor.get("neighbor_address", "N/A")[:21].ljust(21)
            state = neighbor.get("state", "unknown")[:15]

            text.append(f"{intf}{nbr}{state}\n")

    def _display_rsvp(self, text: Text) -> None:
        """Display RSVP sessions."""
        sessions = self.current_data.get("data", {}).get("sessions", [])
        text.append("Destination                      State\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for session in sessions:
            dest = session.get("destination", "N/A")[:33].ljust(33)
            state = session.get("lsp_state", "unknown")[:15]

            text.append(f"{dest}{state}\n")

    def _display_optics(self, text: Text) -> None:
        """Display optical diagnostics."""
        optics = self.current_data.get("data", {}).get("optics", [])
        text.append("Interface            RX Power    TX Power    Temperature\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for optic in optics:
            intf = optic.get("interface", "N/A")[:21].ljust(21)
            rx = optic.get("rx_optical_power", "N/A")[:12].ljust(12)
            tx = optic.get("laser_output_power-dbm", "N/A")[:12].ljust(12)
            temp = optic.get("module_temperature", "N/A")[:12]

            text.append(f"{intf}{rx}{tx}{temp}\n")

    def _display_all(self, text: Text) -> None:
        """Display summary of all fetch results."""
        fetches = self.current_data.get("fetches", {})
        text.append("Type        Status           Count\n", style="dim")
        text.append("────────────────────────────────────────────────────────────\n", style="dim")

        for fetch_type, result in fetches.items():
            ftype = fetch_type.upper()[:12].ljust(12)
            status = result.get("status", "unknown")[:16].ljust(16)

            count = "N/A"
            if result.get("status") == "success":
                data = result.get("data", {})
                if "count" in data:
                    count = str(data["count"])
                elif "interfaces" in data:
                    count = str(len(data["interfaces"]))
                elif "routes" in data:
                    count = str(len(data["routes"]))

            # Color code status
            status_color = "#5aba5a" if result.get("status") == "success" else "#ba5a5a"

            text.append(ftype)
            text.append(status, style=status_color)
            text.append(f"{count}\n")

    def _show_error(self, error_msg: str) -> None:
        """Show error message."""
        content = self.query_one("#fetch-content", FetchContentStatic)
        text = Text()
        text.append("Error\n", style="bold #ba5a5a")
        text.append("─────────────────────────────────────\n\n", style="dim")
        text.append(error_msg, style="#ba5a5a")
        text.append("\n\n─────────────────────────────────────\n\n", style="dim")
        text.append("[q]", style="bold #00d7ff")
        text.append(" Back to options", style="dim")

        content.update(text)

    def on_key(self, event) -> None:
        """Handle key presses in fetch panel."""
        logger.info("fetch_panel_on_key", key=event.key, showing_results=self.showing_results, cursor_index=self.cursor_index)
        print(f"[DEBUG FetchPanel] on_key: {event.key}, showing_results: {self.showing_results}")

        # We only care about specific keys
        if event.key not in ("up", "down", "enter", "q", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a"):
            logger.info("fetch_panel_ignored_key", key=event.key, reason="not_in_allowed_list")
            return

        # Stop event from propagating and prevent default actions
        event.stop()
        event.prevent_default()

        if event.key == "up":
            if self.showing_results:
                logger.info("fetch_panel_ignored_up", reason="showing_results")
                return
            logger.info("fetch_panel_cursor_up", from_index=self.cursor_index)
            print(f"[DEBUG FetchPanel] Moving cursor UP from {self.cursor_index}")
            self.cursor_index = max(0, self.cursor_index - 1)
            content = self.query_one("#fetch-content", FetchContentStatic)
            self._update_options_display(content)

        elif event.key == "down":
            if self.showing_results:
                logger.info("fetch_panel_ignored_down", reason="showing_results")
                return
            logger.info("fetch_panel_cursor_down", from_index=self.cursor_index)
            print(f"[DEBUG FetchPanel] Moving cursor DOWN from {self.cursor_index}")
            self.cursor_index = min(len(self.options) - 1, self.cursor_index + 1)
            content = self.query_one("#fetch-content", FetchContentStatic)
            self._update_options_display(content)

        elif event.key == "enter":
            if self.showing_results:
                return
            if self.current_device and not self.fetching:
                key = self.options[self.cursor_index][0]
                fetch_map = {
                    "1": "facts",
                    "2": "interfaces",
                    "3": "routing",
                    "4": "chassis",
                    "5": "ospf",
                    "6": "bgp",
                    "7": "ldp",
                    "8": "rsvp",
                    "9": "optics",
                    "a": "all",
                }
                fetch_type = fetch_map.get(key)
                if fetch_type:
                    asyncio.create_task(self.fetch_data(self.current_device, fetch_type))

        elif event.key == "q":
            if self.showing_results:
                self._show_options()
            else:
                # Go back to device list
                self.is_active = False  # Mark fetch panel as inactive
                logger.info("fetch_panel_deactivating")
                print(f"[DEBUG FetchPanel] Deactivating, going back to device list")
                try:
                    device_list = self.app.query_one("#dm-device-list")
                    device_list.focus()
                except:
                    pass

        elif event.key in "123456789a":
            if self.showing_results:
                return
            if self.current_device and not self.fetching:
                fetch_map = {
                    "1": "facts",
                    "2": "interfaces",
                    "3": "routing",
                    "4": "chassis",
                    "5": "ospf",
                    "6": "bgp",
                    "7": "ldp",
                    "8": "rsvp",
                    "9": "optics",
                    "a": "all",
                }
                fetch_type = fetch_map.get(event.key)
                if fetch_type:
                    asyncio.create_task(self.fetch_data(self.current_device, fetch_type))

    def _on_key(self, event) -> None:
        """Forward key events from Static to parent."""
        # This will be called by the Static widget
        self.on_key(event)

    def set_device(self, device_host: str) -> None:
        """Set the current device for fetching."""
        self.current_device = device_host
        self.is_active = True  # Mark fetch panel as active
        logger.info("fetch_panel_set_device", device=device_host, is_active=True)
        print(f"[DEBUG FetchPanel] Set device {device_host}, is_active=True")
        if not self.showing_results:
            content = self.query_one("#fetch-content", FetchContentStatic)
            self._update_options_display(content)

    def _move_cursor_up(self) -> None:
        """Move cursor up (called from screen action)."""
        if self.showing_results:
            return
        self.cursor_index = max(0, self.cursor_index - 1)
        content = self.query_one("#fetch-content", FetchContentStatic)
        self._update_options_display(content)

    def handle_key(self, key: str) -> bool:
        """
        Handle a key event from the screen.

        Returns True if the key was handled, False otherwise.
        This method is called by the screen when fetch panel is active.
        """
        logger.info("fetch_panel_handle_key", key=key, is_active=self.is_active)
        print(f"[DEBUG FetchPanel] handle_key: {key}, is_active: {self.is_active}")

        if not self.is_active:
            return False

        # Special handling for 'q' key to return to device list
        if key == "q":
            if self.showing_results:
                # Go back to options
                logger.info("fetch_panel_q_to_options")
                self._show_options()
                return True
            else:
                # Go back to device list - deactivate the panel
                logger.info("fetch_panel_q_to_device_list")
                print(f"[DEBUG FetchPanel] 'q' pressed, deactivating panel")
                self.is_active = False

                # Focus the device list
                try:
                    device_list = self.app.query_one("#dm-device-list")
                    device_list.focus()
                    logger.info("fetch_panel_focused_device_list")
                    print(f"[DEBUG FetchPanel] Focused device list")
                except Exception as e:
                    logger.error("fetch_panel_focus_device_list_error", error=str(e))
                    print(f"[ERROR] Failed to focus device list: {e}")

                return True

        # Create a mock event object for other keys
        class MockEvent:
            def __init__(self, key):
                self.key = key
                self._stopped = False
                self._default_prevented = False

            def stop(self):
                self._stopped = True

            def prevent_default(self):
                self._default_prevented = True

        event = MockEvent(key)
        self.on_key(event)
        return event._stopped

    def _move_cursor_down(self) -> None:
        """Move cursor down (called from screen action)."""
        if self.showing_results:
            return
        self.cursor_index = min(len(self.options) - 1, self.cursor_index + 1)
        content = self.query_one("#fetch-content", FetchContentStatic)
        self._update_options_display(content)
