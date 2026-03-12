"""
Device Management Screen
─────────────────────────
Comprehensive device management interface with grouping, polling, and interface monitoring.
"""

import asyncio
from textual.widgets import Static, Button, Select, DataTable
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.app import ComposeResult
from pathlib import Path
from typing import Optional
from frontend.ui.widgets.device_management_header import DeviceManagementHeader
from frontend.ui.widgets.device_management_footer import DeviceManagementFooter
from frontend.ui.widgets.focus_panel import FocusPanel, FocusableStatic
from frontend.ui.widgets.activity_log import ActivityLog
from frontend.ui.widgets.device_list_widget import DeviceListWidget
from textual.reactive import reactive


class PollingPanel(FocusableStatic):
    """Widget displaying polling status and controls."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.polling_enabled = False
        self.polling_interval = "5m"
        self.fiber_mode = "Both"  # Both, SM, MM

    def on_mount(self) -> None:
        """Initialize the polling panel."""
        self.update_content()

    def update_content(self) -> None:
        """Update the polling panel display."""
        from rich.text import Text

        # Create a Rich Text object
        content = Text()

        # Status
        status_color = "green" if self.polling_enabled else "red"
        status_text = "ON" if self.polling_enabled else "OFF"
        content.append("STATUS: ", style="bold")
        content.append(status_text + "\n", style=f"bold on {status_color}")

        # Interval
        content.append("Interval: 5m\n\n", style="dim")

        # Presets with colored brackets on one line
        content.append("Presets: ", style="bold")
        content.append("[1]", style="bold #00d7ff")
        content.append(" 1m, ", style="bold")
        content.append("[2]", style="bold #00d7ff")
        content.append(" 5m, ", style="bold")
        content.append("[3]", style="bold #00d7ff")
        content.append(" 10m, ", style="bold")
        content.append("[4]", style="bold #00d7ff")
        content.append(" 15m\n\n", style="bold")

        # Fiber with bracketed SM and MM
        content.append("Fiber: Both ", style="bold")
        content.append("[SM]", style="bold #00d7ff")
        content.append(" ", style="bold")
        content.append("[MM]\n", style="bold #00d7ff")
        content.append("─────────────────────────────────────\n\n", style="dim")

        # Keyboard shortcuts with colored brackets
        content.append("[p]", style="bold #00d7ff")
        content.append(" Toggle polling on/off\n", style="dim")

        content.append("[f]", style="bold #00d7ff")
        content.append(" Fetch now (one-shot)\n", style="dim")

        content.append("[s]", style="bold #00d7ff")
        content.append(" Cycle fiber mode filter\n", style="dim")

        content.append("[r]", style="bold #00d7ff")
        content.append(" Rescan SFP transceivers\n", style="dim")

        content.append("[c]", style="bold #00d7ff")
        content.append(" Connect new device\n", style="dim")

        content.append("[d]", style="bold #00d7ff")
        content.append(" Disconnect", style="dim")

        # Update the widget with the Rich Text object
        self.update(content)

    def toggle_polling(self) -> None:
        """Toggle polling on/off."""
        self.polling_enabled = not self.polling_enabled
        self.update_content()

    def set_interval(self, interval: str) -> None:
        """Set polling interval."""
        self.polling_interval = interval
        self.update_content()

    def cycle_fiber_mode(self) -> None:
        """Cycle through fiber modes: Both -> SM -> MM -> Both"""
        modes = ["Both", "SM", "MM"]
        current_index = modes.index(self.fiber_mode)
        self.fiber_mode = modes[(current_index + 1) % len(modes)]
        self.update_content()

    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "p":
            self.toggle_polling()
            self.app.notify(f"Polling {'enabled' if self.polling_enabled else 'disabled'}", severity="information")
        elif event.key == "f":
            self.app.notify("Fetching data from all devices...", severity="information")
        elif event.key == "s":
            self.cycle_fiber_mode()
            self.app.notify(f"Fiber mode: {self.fiber_mode}", severity="information")
        elif event.key == "r":
            self.app.notify("Rescanning SFP transceivers...", severity="information")
        elif event.key == "c":
            self.app.notify("Opening connection dialog...", severity="information")
        elif event.key == "d":
            self.app.notify("Disconnecting devices...", severity="warning")


class InterfaceList(DataTable):
    """Widget displaying interface information."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = False  # Disabled for pure black background

    def on_mount(self) -> None:
        """Initialize the interface table - empty initially."""
        # Don't add columns initially - will be populated when data is fetched
        self.border_subtitle = ""  # Clear any subtitle

    def update_interfaces(self, interfaces: dict) -> None:
        """Update the interface table with data."""
        # Clear existing columns and rows
        self.clear(columns=True)

        if not interfaces:
            self.update("No interfaces available")
            return

        # Add columns
        self.add_columns("Interface", "Status", "RX Power", "TX Power", "Errors", "Flaps")

        # Add rows
        for intf_name, intf_data in interfaces.items():
            status = intf_data.get("oper_status", "unknown")
            rx_power = intf_data.get("optics", {}).get("rx_optical_power-dbm", "N/A")
            tx_power = intf_data.get("optics", {}).get("laser_output_power-dbm", "N/A")
            errors = intf_data.get("stats", {}).get("crc_errors", "0")
            flaps = intf_data.get("stats", {}).get("flaps", "0")

            # Color code status
            status_color = {
                "up": "#00ff00",
                "down": "#ff0000",
                "unknown": "#888888"
            }.get(status.lower(), "#ffffff")

            self.add_row(
                f"[#ffffff]{intf_name}[/]",
                f"[{status_color}]{status.upper()}[/]",
                f"[#ffffff]{rx_power}[/]",
                f"[#ffffff]{tx_power}[/]",
                f"[#ffffff]{errors}[/]",
                f"[#ffffff]{flaps}[/]"
            )


class DeviceDetails(FocusableStatic):
    """Widget showing device details."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_data = {}

    def update_details(self, data: dict) -> None:
        """Update the device details."""
        self.current_data = data

        facts = data.get("facts", {})
        interfaces = data.get("interfaces", {})

        content = [
            "[#0088ff]Device Information[/]",
            f"Hostname: {facts.get('hostname', 'N/A')}",
            f"Model: {facts.get('model', 'N/A')}",
            f"Serial: {facts.get('serialnumber', 'N/A')}",
            f"OS Version: {facts.get('version', 'N/A')}",
            f"Uptime: {facts.get('uptime', 'N/A')}",
            "",
            f"[#0088ff]Interfaces ({len(interfaces)})[/]"
        ]

        for intf_name, intf_data in list(interfaces.items())[:10]:  # Show first 10
            status = intf_data.get("oper_status", "unknown")
            rx_power = intf_data.get("optics", {}).get("rx_optical_power-dbm", "N/A")
            errors = intf_data.get("stats", {}).get("crc_errors", "0")
            content.append(f"  {intf_name}: {status} | RX: {rx_power} | Errors: {errors}")

        if len(interfaces) > 10:
            content.append(f"  ... and {len(interfaces) - 10} more")

        self.update("\n".join(content))


class DeviceManagementScreen(Screen):
    """Device management screen with grouping and polling capabilities."""

    # Load stylesheets
    _PANELS_CSS = Path(__file__).parent.parent / "styles" / "panels.tcss"
    _SCREEN_CSS = Path(__file__).parent.parent / "styles" / "device_management.tcss"
    _TITLE_CSS = Path(__file__).parent.parent / "styles" / "title_field.tcss"
    _ACTIVITY_CSS = Path(__file__).parent.parent / "styles" / "activity_log.tcss"
    _DEVICE_LIST_CSS = Path(__file__).parent.parent / "styles" / "device_list_widget.tcss"

    CSS = ""
    if _PANELS_CSS.exists():
        CSS += _PANELS_CSS.read_text()
    if _SCREEN_CSS.exists():
        CSS += _SCREEN_CSS.read_text()
    if _TITLE_CSS.exists():
        CSS += _TITLE_CSS.read_text()
    if _ACTIVITY_CSS.exists():
        CSS += _ACTIVITY_CSS.read_text()
    if _DEVICE_LIST_CSS.exists():
        CSS += _DEVICE_LIST_CSS.read_text()

    BINDINGS = [
        ("p", "toggle_polling", "Toggle Polling"),
        ("f", "fetch_now", "Fetch Now"),
        ("s", "cycle_fiber", "Cycle Fiber Mode"),
        ("r", "rescan_sfps", "Rescan SFPs"),
        ("c", "connect_device", "Connect Device"),
        ("d", "disconnect_devices", "Disconnect"),
    ]

    polling_interval = reactive("MANUAL")

    def compose(self) -> ComposeResult:
        """Compose the device management layout with 2x2 grid."""
        # Use Vertical container for proper layout
        with Vertical(id="dm-container"):
            # Header
            yield DeviceManagementHeader(id="dm-header")

            # 2x2 Grid layout
            with Vertical(id="dm-main"):
                # Top row: Sessions (left, wider) and Interfaces (right)
                with Horizontal(id="dm-top-row"):
                    # Top left: Sessions (wider)
                    with FocusPanel("Sessions", id="dm-sessions-panel"):
                        yield DeviceListWidget(id="dm-device-list")

                    # Top right: Interfaces
                    with FocusPanel("Interfaces", id="dm-interfaces-panel"):
                        yield InterfaceList(id="dm-interface-list")

                # Bottom row: Activity Log (left, wider) and Polling (right)
                with Horizontal(id="dm-bottom-row"):
                    # Bottom left: Activity Log (wider)
                    with FocusPanel("Activity Log", id="dm-activity-panel"):
                        yield ActivityLog(id="dm-activity-log")

                    # Bottom right: Polling
                    with FocusPanel("Polling", id="dm-polling-panel"):
                        yield PollingPanel(id="dm-polling-status")

            # Footer
            yield DeviceManagementFooter(id="dm-footer")

    async def on_mount(self) -> None:
        """Initialize the device management screen."""
        # Get device manager from app
        self.device_manager = getattr(self.app, 'device_manager', None)
        if not self.device_manager:
            self.notify("Device manager not available", severity="error")

        # Start polling updates
        self.set_interval(1, self._update_header)

        # Device list and activity log widgets handle their own event subscriptions

    def _update_header(self) -> None:
        """Update header with current device counts."""
        try:
            header = self.query_one("#dm-header", DeviceManagementHeader)

            if self.device_manager:
                counts = self.device_manager.get_device_counts()
                header.set_device_counts(
                    total=counts["total"],
                    connected=counts["connected"],
                    failed=counts["failed"]
                )
        except Exception:
            pass

    def action_toggle_polling(self) -> None:
        """Toggle polling on/off."""
        try:
            polling_panel = self.query_one("#dm-polling-status", PollingPanel)
            polling_panel.toggle_polling()
        except Exception:
            pass

    def action_fetch_now(self) -> None:
        """Fetch data from all devices now (one-shot)."""
        self._fetch_all_devices()

    def action_cycle_fiber(self) -> None:
        """Cycle fiber mode filter."""
        try:
            polling_panel = self.query_one("#dm-polling-status", PollingPanel)
            polling_panel.cycle_fiber_mode()
        except Exception:
            pass

    def action_rescan_sfps(self) -> None:
        """Rescan SFP transceivers."""
        self.notify("Resanning SFP transceivers...", severity="information")
        # TODO: Implement SFP rescan

    def action_connect_device(self) -> None:
        """Open connection dialog."""
        self.notify("Opening connection dialog...", severity="information")
        self.app.push_screen("connection")

    def action_disconnect_devices(self) -> None:
        """Disconnect all devices."""
        try:
            if hasattr(self.app, 'conn_mgr') and self.app.conn_mgr:
                # Disconnect all sessions
                for host in list(self.app.conn_mgr.sessions.keys()):
                    self.app.conn_mgr.disconnect_device(host)

                self.notify("Disconnected all devices", severity="information")

                # Device list auto-updates via events, but refresh to be sure
                device_list = self.query_one("#dm-device-list", DeviceListWidget)
                device_list.refresh_devices()
            else:
                self.notify("No devices to disconnect", severity="warning")
        except Exception as e:
            self.notify(f"Disconnect failed: {str(e)}", severity="error")

    async def _fetch_all_devices(self) -> None:
        """Fetch data from all connected devices."""
        if not self.device_manager:
            self.notify("Device manager not available", severity="error")
            return

        self.notify("Fetching data from all devices...", severity="information")

        # Log to activity log
        try:
            activity_log = self.query_one("#dm-activity-log", ActivityLog)
            activity_log.write_line("[INFO] Fetching data from all devices...")

            try:
                results = await self.device_manager.poll_all_devices()

                success_count = len(results["success"])
                failed_count = len(results["failed"])

                if success_count > 0:
                    self.notify(f"Successfully fetched data from {success_count} device(s)", severity="success")
                    activity_log.write_line(f"[SUCCESS] Fetched data from {success_count} device(s)")

                if failed_count > 0:
                    self.notify(f"Failed to fetch from {failed_count} device(s)", severity="error")
                    activity_log.write_line(f"[ERROR] Failed to fetch from {failed_count} device(s)")

                # Update UI with fetched data
                self._update_device_data(results["data"])

            except Exception as e:
                self.notify(f"Fetch failed: {str(e)}", severity="error")
                activity_log.write_line(f"[ERROR] Fetch failed: {str(e)}")
        except Exception:
            pass

    def _set_polling_interval(self, interval: str) -> None:
        """Set the polling interval."""
        if not self.device_manager:
            return

        # Convert string to PollingInterval
        from backend.core.device_manager import PollingInterval

        interval_map = {
            "MANUAL": PollingInterval.MANUAL,
            "1m": PollingInterval.ONE_MIN,
            "3m": PollingInterval.THREE_MIN,
            "5m": PollingInterval.FIVE_MIN,
            "10m": PollingInterval.TEN_MIN,
            "15m": PollingInterval.FIFTEEN_MIN
        }

        polling_interval = interval_map.get(interval, PollingInterval.MANUAL)

        asyncio.create_task(self.device_manager.set_polling_interval(polling_interval))
        self.notify(f"Polling set to {interval}", severity="information")

        # Update polling status display
        try:
            polling_status = self.query_one("#dm-polling-status", Static)
            polling_status.update(f"Polling Status: {interval}\n\nLast Poll: In progress...\nPolls: 0")
        except Exception:
            pass

    def _update_device_data(self, data: dict) -> None:
        """Update the UI with fetched device data."""
        try:
            # Device list auto-updates from sessions, so just refresh it
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            device_list.refresh_devices()

            # Update interface table with all interfaces from all devices
            interface_list = self.query_one("#dm-interface-list", InterfaceList)
            all_interfaces = {}

            for host, host_data in data.items():
                interfaces = host_data.get("interfaces", {})
                for intf_name, intf_data in interfaces.items():
                    # Prefix with hostname to show which device
                    all_interfaces[f"{host}:{intf_name}"] = intf_data

            interface_list.update_interfaces(all_interfaces)

            # Update polling stats
            if self.device_manager:
                stats = self.device_manager.get_polling_stats()
                try:
                    polling_panel = self.query_one("#dm-polling-status", PollingPanel)
                    polling_panel.set_interval(stats['interval'])
                except Exception:
                    pass

        except Exception as e:
            self.notify(f"Failed to update UI: {str(e)}", severity="error")
