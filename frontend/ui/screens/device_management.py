"""
Device Management Screen
─────────────────────────
Comprehensive device management interface with grouping, polling, and interface monitoring.
"""

import asyncio
from textual.widgets import Static, Button, Select
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
from backend.utils.logging import logger


class PollingAndControlsPanel(FocusableStatic):
    """Combined widget displaying polling status and keyboard shortcuts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.polling_enabled = False
        self.polling_interval = "5m"
        self.fiber_mode = "Both"  # Both, SM, MM

    def on_mount(self) -> None:
        """Initialize the polling and controls panel."""
        self.update_content()

    def update_content(self) -> None:
        """Update the polling and controls panel display."""
        from rich.text import Text

        content = Text()

        # === POLLING SECTION ===
        # Status
        status_color = "green" if self.polling_enabled else "red"
        status_text = "ON" if self.polling_enabled else "OFF"
        content.append("STATUS: ", style="bold")
        content.append(status_text + "\n", style=f"bold on {status_color}")

        # Interval
        content.append("Interval: 5m\n", style="dim")

        # Presets - more compact with separate styling
        content.append("[1]", style="bold #00d7ff")
        content.append("1m ", style="dim #888888")
        content.append("[2]", style="bold #00d7ff")
        content.append("5m ", style="dim #888888")
        content.append("[3]", style="bold #00d7ff")
        content.append("10m ", style="dim #888888")
        content.append("[4]", style="bold #00d7ff")
        content.append("15m\n", style="dim #888888")

        # Fiber - more compact
        content.append("Fiber: ", style="bold")
        content.append("[SM]", style="bold #00d7ff")
        content.append(" ", style="bold")
        content.append("[MM]\n", style="bold #00d7ff")

        # Separator
        content.append("─────────────\n", style="dim")

        # === CONTROLS SECTION ===
        # More compact format - blue keys, gray descriptions
        content.append("[p]", style="bold #00d7ff")
        content.append("Toggle\n", style="dim #888888")
        content.append("[f]", style="bold #00d7ff")
        content.append("Fetch\n", style="dim #888888")
        content.append("[s]", style="bold #00d7ff")
        content.append("Fiber\n", style="dim #888888")
        content.append("[r]", style="bold #00d7ff")
        content.append("Rescan\n", style="dim #888888")
        content.append("[c]", style="bold #00d7ff")
        content.append("Connect\n", style="dim #888888")
        content.append("[d]", style="bold #00d7ff")
        content.append("Disconnect\n", style="dim #888888")
        content.append("[x]", style="bold #00d7ff")
        content.append("Delete Failed\n", style="dim #888888")

        # Update the widget
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
        elif event.key == "s":
            self.cycle_fiber_mode()
            self.app.notify(f"Fiber mode: {self.fiber_mode}", severity="information")
        elif event.key == "r":
            self.app.notify("Rescanning SFP transceivers...", severity="information")
        elif event.key == "c":
            self.app.notify("Opening connection dialog...", severity="information")
        elif event.key == "d":
            self.app.notify("Disconnecting devices...", severity="warning")
        elif event.key == "x":
            # Call the screen's action to delete failed sessions
            self.app.action_delete_failed()


class DeviceManagementScreen(Screen):
    """Device management screen with grouping and polling capabilities."""

    # Load stylesheets
    _PANELS_CSS = Path(__file__).parent.parent / "styles" / "panels.tcss"
    _SCREEN_CSS = Path(__file__).parent.parent / "styles" / "device_management.tcss"
    _TITLE_CSS = Path(__file__).parent.parent / "styles" / "title_field.tcss"
    _ACTIVITY_CSS = Path(__file__).parent.parent / "styles" / "activity_log.tcss"
    _DEVICE_LIST_CSS = Path(__file__).parent.parent / "styles" / "device_list_widget.tcss"
    _FETCH_PANEL_CSS = Path(__file__).parent.parent / "styles" / "fetch_panel.tcss"
    _MODULAR_FOOTER_CSS = Path(__file__).parent.parent / "styles" / "modular_footer.tcss"
    _MODULAR_HEADER_CSS = Path(__file__).parent.parent / "styles" / "modular_header.tcss"

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
    if _FETCH_PANEL_CSS.exists():
        CSS += _FETCH_PANEL_CSS.read_text()
    if _MODULAR_FOOTER_CSS.exists():
        CSS += _MODULAR_FOOTER_CSS.read_text()
    if _MODULAR_HEADER_CSS.exists():
        CSS += _MODULAR_HEADER_CSS.read_text()

    BINDINGS = [
        ("c", "connect_device", "Connect Device"),
        ("p", "toggle_polling", "Toggle Polling"),
        ("f", "fetch_now", "Fetch Now"),
        ("s", "cycle_fiber", "Cycle Fiber Mode"),
        ("r", "rescan_sfps", "Rescan SFPs"),
        ("d", "disconnect_selected", "Disconnect Selected"),
        ("x", "delete_failed", "Delete Failed Sessions"),
    ]

    polling_interval = reactive("MANUAL")

    def compose(self) -> ComposeResult:
        """Compose the device management layout with 2x2 grid."""
        # Use Vertical container for proper layout
        with Vertical(id="dm-container"):
            # Header
            yield DeviceManagementHeader(id="dm-header")

            # New 2x2 Grid layout with combined panel
            with Vertical(id="dm-main"):
                # Top row: Sessions (left, larger) and Polling & Controls (right)
                with Horizontal(id="dm-top-row"):
                    # Top left: Sessions (larger - 70%)
                    with FocusPanel("Sessions", id="dm-sessions-panel"):
                        yield DeviceListWidget(id="dm-device-list")

                    # Top right: Polling & Controls (combined - 35%)
                    with FocusPanel("Controls", id="dm-polling-controls-panel"):
                        yield PollingAndControlsPanel(id="dm-polling-controls")

            # Bottom: Activity Log (full width)
            with Vertical(id="dm-bottom-row"):
                with FocusPanel("Activity Log", id="dm-activity-panel"):
                    yield ActivityLog(id="dm-activity-log")

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

    def on_key(self, event) -> None:
        """Handle key events at screen level for device list navigation."""
        # Handle up/down for device list
        if event.key == "up":
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            device_list.cursor_up()
            device_list.focus()
            event.stop()
        elif event.key == "down":
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            device_list.cursor_down()
            device_list.focus()
            event.stop()

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
            polling_panel = self.query_one("#dm-polling-controls", PollingAndControlsPanel)
            polling_panel.toggle_polling()
        except Exception:
            pass

    def action_fetch_now(self) -> None:
        """Open fetch results screen for selected device."""
        logger.info("action_fetch_now_called")
        print("[DEBUG] action_fetch_now called")

        try:
            # Get selected device
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            selected_device = device_list.get_selected_device()

            if not selected_device:
                self.notify("No device selected", severity="warning")
                logger.warning("fetch_no_device_selected")
                return

            logger.info("fetch_device_selected", device=selected_device)

            # Check if device is connected
            if hasattr(self.app, 'conn_mgr') and self.app.conn_mgr:
                session = self.app.conn_mgr.sessions.get(selected_device)
                if not session or session.state.value != "CONNECTED":
                    self.notify(f"Device {selected_device} is not connected", severity="warning")
                    logger.warning("fetch_device_not_connected", device=selected_device)
                    return

            logger.info("fetch_device_connected", device=selected_device)

            # Import and push the FetchResultsScreen
            from frontend.ui.screens.fetch_results import FetchResultsScreen

            fetch_screen = FetchResultsScreen(device=selected_device)
            self.app.push_screen(fetch_screen)

            logger.info("fetch_results_screen_pushed", device=selected_device)
            print(f"[DEBUG] Pushed FetchResultsScreen for {selected_device}")

        except Exception as e:
            logger.error("fetch_set_device_error", error=str(e))
            print(f"[ERROR] Failed to open fetch results: {e}")
            import traceback
            traceback.print_exc()
            self.notify(f"Failed to open fetch results: {str(e)}", severity="error")

    def action_cycle_fiber(self) -> None:
        """Cycle fiber mode filter."""
        try:
            polling_panel = self.query_one("#dm-polling-controls", PollingAndControlsPanel)
            polling_panel.cycle_fiber_mode()
        except Exception:
            pass

    def action_rescan_sfps(self) -> None:
        """Rescan SFP transceivers."""
        self.notify("Resanning SFP transceivers...", severity="information")
        # TODO: Implement SFP rescan

    def action_connect_device(self) -> None:
        """Open connection dialog."""
        logger.info("action_connect_device_called")
        print("[DEBUG] action_connect_device called")

        self.notify("Opening connection dialog...", severity="information")

        def handle_result(result):
            logger.info("connection_form_result", result=result)
            print(f"[DEBUG] Connection form result: {result}")

            if result and hasattr(self.app, 'connect_to_new_devices'):
                print(f"[DEBUG] Calling connect_to_new_devices with {result}")
                asyncio.create_task(self.app.connect_to_new_devices(result))

        try:
            print("[DEBUG] Pushing connection screen via app")
            screen = self.app.push_screen("connection", handle_result)
            print(f"[DEBUG] Connection screen pushed, returned: {screen}")
        except Exception as e:
            logger.error("push_screen_error", error=str(e))
            print(f"[ERROR] Failed to push screen: {e}")
            self.notify(f"Failed to open connection dialog: {e}", severity="error")

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

    def action_cursor_up(self) -> None:
        """Move cursor up in device list."""
        try:
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            device_list.cursor_up()
            device_list.focus()
        except Exception as e:
            logger.error("cursor_up_error", error=str(e))

    def action_cursor_down(self) -> None:
        """Move cursor down in device list."""
        try:
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            device_list.cursor_down()
            device_list.focus()
        except Exception as e:
            logger.error("cursor_down_error", error=str(e))

    def action_disconnect_selected(self) -> None:
        """Disconnect the selected device."""
        try:
            device_list = self.query_one("#dm-device-list", DeviceListWidget)
            selected_device = device_list.get_selected_device()

            if not selected_device:
                self.notify("No device selected", severity="warning")
                logger.warning("disconnect_failed_no_device_selected")
                return

            logger.info("disconnecting_selected_device", device=selected_device)
            print(f"[DEBUG] Disconnecting device: {selected_device}")

            if hasattr(self.app, 'conn_mgr') and self.app.conn_mgr:
                # Log to activity log
                try:
                    activity_log = self.query_one("#dm-activity-log", ActivityLog)
                    activity_log.add_entry(f"Disconnecting {selected_device}...", "warning")
                except Exception:
                    pass

                # Disconnect the device
                asyncio.create_task(self.app.conn_mgr.disconnect_device(selected_device))
                self.notify(f"Disconnecting {selected_device}...", severity="information")
                logger.info("disconnect_initiated", device=selected_device)
            else:
                logger.error("disconnect_failed_conn_mgr_not_available")
                self.notify("Connection manager not available", severity="error")
        except Exception as e:
            logger.error("disconnect_selected_error", error=str(e))
            print(f"[ERROR] Disconnect failed: {e}")
            import traceback
            traceback.print_exc()
            self.notify(f"Disconnect failed: {str(e)}", severity="error")

    def action_delete_failed(self) -> None:
        """Delete all failed/disconnected sessions."""
        try:
            if not hasattr(self.app, 'conn_mgr') or not self.app.conn_mgr:
                self.notify("Connection manager not available", severity="error")
                return

            conn_mgr = self.app.conn_mgr
            sessions = conn_mgr.sessions

            # Find all failed or disconnected sessions
            failed_devices = []
            for host, session in sessions.items():
                state = session.state.value if hasattr(session, 'state') else "UNKNOWN"
                if state in ["FAILED", "DISCONNECTED"]:
                    failed_devices.append(host)

            if not failed_devices:
                self.notify("No failed sessions to delete", severity="information")
                logger.info("delete_failed_no_sessions")
                return

            logger.info("delete_failed_initiated", count=len(failed_devices), devices=failed_devices)

            # Log to activity log
            try:
                activity_log = self.query_one("#dm-activity-log", ActivityLog)
                activity_log.add_entry(f"Deleting {len(failed_devices)} failed session(s)...", "warning")
            except Exception:
                pass

            # Delete all failed sessions
            deleted_count = 0
            for host in failed_devices:
                try:
                    del conn_mgr.sessions[host]
                    deleted_count += 1
                    logger.info("delete_failed_success", device=host)
                except Exception as e:
                    logger.error("delete_failed_device_error", device=host, error=str(e))

            self.notify(f"Deleted {deleted_count} failed session(s)", severity="success")

            # Refresh the device list
            try:
                device_list = self.query_one("#dm-device-list", DeviceListWidget)
                device_list.refresh_devices()
            except Exception:
                pass

        except Exception as e:
            logger.error("delete_failed_error", error=str(e))
            print(f"[ERROR] Delete failed: {e}")
            import traceback
            traceback.print_exc()
            self.notify(f"Delete failed: {str(e)}", severity="error")

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
