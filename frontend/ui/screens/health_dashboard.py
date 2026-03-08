"""
health_dashboard.py
───────────────────
Circuit Health Dashboard Screen - Modular grid layout.

Pure black theme with thin borders and border-titles for space efficiency.
Panels are modular and can be easily added/removed/rearranged.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Static, Button

from frontend.ui.widgets.pulse_widgets import PulsePanel, MetricBar, StatusBadge, CompactTable, CompactLog
from frontend.ui.widgets.pulse_header import PulseHeader
from backend.utils.logging import logger
from frontend.ui.widgets.health_metrics import (
    HealthMetricBar,
    StatusBadgeWithTrend,
    OpticalMetricsTable,
    ComponentScoresPanel,
    TrendIndicator,
)


class HealthDashboardScreen(Screen):
    """Circuit Health Dashboard with modular grid layout."""

    TITLE = "Circuit Health"
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
    ]

    # Load CSS from file
    _CSS_PATH = Path(__file__).parent.parent / "styles" / "health_dashboard.tcss"
    CSS = _CSS_PATH.read_text() if _CSS_PATH.exists() else ""

    def compose(self) -> ComposeResult:
        """Compose the dashboard grid."""
        yield PulseHeader(id="pulse-header")
        yield Footer()

        # Top bar with title and fetch button
        with Horizontal(id="top-bar"):
            yield Static("Circuit Health", id="dashboard-title")
            yield Button("FETCH", id="fetch-button")

        # Main grid container
        with Vertical(id="dashboard-grid"):
            # Row 1
            with Horizontal():
                # Left column: Health Scores (top) and Network Summary (bottom)
                with Vertical():
                    yield HealthScoresPanel(id="health-scores")
                    yield NetworkSummaryPanel(id="network-summary")
                # Right column: Optical Diagnostics split horizontally
                with Vertical():
                    yield OpticalDiagnosticsPanel(id="optics-table")
                    yield OpticalStatsPanel(id="optics-stats")

            # Row 2
            with Horizontal():
                yield InterfaceDetailsPanel(id="interface-details")
                yield AlertHistoryPanel(id="alert-history")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "fetch-button":
            await self.fetch_data()

    async def fetch_data(self) -> None:
        """Fetch data from connected devices."""
        try:
            # Disable button and show progress
            button = self.query_one("#fetch-button", Button)
            button.disabled = True
            button.label = "⏳ Fetching..."

            # Get alert panel for messages
            alert_panel = self.query_one("#alert-history", AlertHistoryPanel)
            alert_panel.add_alert("=" * 50, "info")
            alert_panel.add_alert("📡 Starting data fetch...", "info")

            # Get the app's connection manager
            app = self.app
            if not hasattr(app, 'conn_mgr'):
                alert_panel.add_alert("❌ No connection manager found", "error")
                button.disabled = False
                button.label = "FETCH"
                return

            conn_mgr = app.conn_mgr
            alert_panel.add_alert(f"Found {len(conn_mgr.sessions)} session(s)", "info")

            # Debug: List all sessions and their states
            for host, session in conn_mgr.sessions.items():
                alert_panel.add_alert(f"  - {host}: {session.state.value}", "info")

            connected_devices = [
                host for host, session in conn_mgr.sessions.items()
                if session.state.value == "CONNECTED"
            ]

            if not connected_devices:
                alert_panel.add_alert("", "info")
                alert_panel.add_alert("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
                alert_panel.add_alert("❌ No devices connected!", "error")
                alert_panel.add_alert("", "info")
                alert_panel.add_alert("To fetch data:", "info")
                alert_panel.add_alert("  1. Press 'Esc' to exit this dashboard", "info")
                alert_panel.add_alert("  2. Press 'c' to open the connection form", "info")
                alert_panel.add_alert("  3. Enter device credentials and connect", "info")
                alert_panel.add_alert("  4. Press 'h' to return to this dashboard", "info")
                alert_panel.add_alert("  5. Press 'FETCH' again", "info")
                alert_panel.add_alert("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "info")
                alert_panel.add_alert("", "info")

                button.disabled = False
                button.label = "FETCH"
                return

            alert_panel.add_alert("", "info")
            alert_panel.add_alert(f"✓ {len(connected_devices)} device(s) connected", "success")
            alert_panel.add_alert("", "info")

            # Import optical diagnostics engine
            from backend.core.optical_diagnostics import OpticalDiagnosticsEngine
            optics_engine = OpticalDiagnosticsEngine(conn_mgr)

            # Import interface discovery
            from backend.core.interface_discovery import InterfaceDiscovery
            discovery = InterfaceDiscovery(conn_mgr, cache_ttl=300)

            all_data = {}

            for idx, device in enumerate(connected_devices):
                alert_panel.add_alert(f"📡 [{idx+1}/{len(connected_devices)}] {device}", "info")

                try:
                    # Step 1: Get chassis hardware to identify LR SFPs
                    alert_panel.add_alert(f"  → Scanning for LR SFP modules...", "info")

                    chassis_hardware = await optics_engine.get_chassis_hardware(device)
                    if not chassis_hardware:
                        alert_panel.add_alert(f"    ⚠ Could not read chassis hardware", "warning")
                        continue

                    # Step 2: Parse to find interfaces with LR SFPs
                    lr_interfaces = optics_engine.get_lr_interfaces(chassis_hardware)

                    if not lr_interfaces:
                        alert_panel.add_alert(f"    ⚠ No LR SFP modules found (10G-LR, 100G-LR)", "warning")
                        continue

                    alert_panel.add_alert(f"    ✓ Found {len(lr_interfaces)} LR SFP interface(s)", "success")

                    # Step 3: Get operational status for these interfaces
                    alert_panel.add_alert(f"  → Checking interface status...", "info")

                    discovery_result = await discovery.get_interfaces(device)

                    if discovery_result.get("status") != "success":
                        alert_panel.add_alert(f"    ❌ Discovery failed: {discovery_result.get('error', 'Unknown')}", "error")
                        continue

                    all_interfaces = discovery_result.get("interfaces", [])
                    iface_status_map = {iface["name"]: iface for iface in all_interfaces}

                    # Combine LR interfaces with their status
                    lr_ifaces_with_status = []
                    for iface_name, sfp_info in lr_interfaces.items():
                        iface_info = iface_status_map.get(iface_name, {
                            "name": iface_name,
                            "oper_status": "unknown",
                            "description": ""
                        })
                        iface_info["sfp_info"] = sfp_info
                        lr_ifaces_with_status.append(iface_info)

                    # Filter to interfaces that are UP - prioritize these for optical diagnostics
                    up_ifaces = [iface for iface in lr_ifaces_with_status if iface.get("oper_status") == "up"]
                    down_ifaces = [iface for iface in lr_ifaces_with_status if iface.get("oper_status") != "up"]

                    if up_ifaces:
                        alert_panel.add_alert(
                            f"    ✓ {len(up_ifaces)} carrier interface(s) UP, {len(down_ifaces)} down",
                            "success"
                        )
                    else:
                        alert_panel.add_alert(f"    ⚠ All carrier interfaces are down!", "warning")

                    device_data = []
                    for idx, iface in enumerate(lr_ifaces_with_status[:10]):  # Limit to first 10 interfaces
                        iface_name = iface["name"]
                        oper_status = iface.get("oper_status", "unknown")
                        sfp_desc = iface.get("sfp_info", {}).get("description", "Unknown SFP")
                        sfp_serial = iface.get("sfp_info", {}).get("serial_number", "")

                        # Show SFP info in log
                        if oper_status == "up":
                            alert_panel.add_alert(
                                f"      → [{idx+1}/{len(lr_ifaces_with_status)}] {iface_name} ({oper_status}) [{sfp_desc}]",
                                "info"
                            )
                        else:
                            alert_panel.add_alert(
                                f"      → [{idx+1}/{len(lr_ifaces_with_status)}] {iface_name} ({oper_status}) [{sfp_desc}] SN:{sfp_serial}",
                                "warning"
                            )

                        # Fetch optical diagnostics (only if UP or to check why it's down)
                        if oper_status == "up":
                            optics = await optics_engine.get_optical_diagnostics(device, iface_name)
                            if optics:
                                alert_panel.add_alert(
                                    f"          TX: {optics.laser_output_power_dbm:+.1f}dBm, "
                                    f"RX: {optics.rx_signal_power_dbm:+.1f}dBm, "
                                    f"Temp: {optics.module_temperature:.0f}°C",
                                    "success"
                                )

                                # Calculate health score based on optical data
                                score = 100
                                severity = "INFO"
                                trend = "STABLE"

                                # Check RX power
                                rx_power = optics.rx_signal_power_dbm
                                if rx_power < -15:
                                    score = 30
                                    severity = "CRITICAL"
                                    trend = "DEGRADING"
                                elif rx_power < -12:
                                    score = 60
                                    severity = "WARNING"
                                    trend = "STABLE"
                                elif rx_power < -8:
                                    score = 85
                                    severity = "INFO"
                                    trend = "STABLE"

                                # Check for alarms
                                if optics.rx_power_low_alarm or optics.tx_power_low_alarm:
                                    score = min(score, 20)
                                    severity = "CRITICAL"
                                    trend = "CRITICAL"
                                elif optics.rx_power_low_warn or optics.tx_power_low_warn:
                                    score = min(score, 50)
                                    if severity != "CRITICAL":
                                        severity = "WARNING"

                                device_data.append({
                                    "interface_name": iface_name,
                                    "score": score,
                                    "severity": severity,
                                    "trend_direction": trend,
                                    "optical_score": optics.rx_signal_power_dbm,
                                    "tx_power": optics.laser_output_power_dbm,
                                    "rx_power": optics.rx_signal_power_dbm,
                                    "temperature": optics.module_temperature,
                                    "description": f"{sfp_desc} ({sfp_serial})",
                                })
                            else:
                                alert_panel.add_alert(f"          ⚠ No optical data available", "warning")
                        else:
                            # Interface is down - try to get statistics to see why
                            alert_panel.add_alert(f"          ⚠ Interface down - checking stats...", "warning")

                            stats = await optics_engine.get_interface_statistics(device, iface_name)
                            if stats:
                                # Calculate how long it's been down
                                time_str = "Unknown"
                                if stats.interface_flapped:
                                    time_str = stats.interface_flapped
                                elif oper_status == "down":
                                    time_str = "Down"

                                flap_info = f"Last flap: {time_str}" if stats.interface_flapped else "No flap info"
                                alert_panel.add_alert(
                                    f"          ℹ {flap_info}, Carrier transitions: {stats.carrier_transitions}",
                                    "info"
                                )

                                # Still add to data with a score of 0
                                device_data.append({
                                    "interface_name": iface_name,
                                    "score": 0,
                                    "severity": "CRITICAL",
                                    "trend_direction": "DOWN",
                                    "optical_score": -99.9,
                                    "tx_power": -99.9,
                                    "rx_power": -99.9,
                                    "temperature": 0,
                                    "description": f"{sfp_desc} - {flap_info}",
                                })
                            else:
                                alert_panel.add_alert(f"          ⚠ No statistics available", "warning")
                                device_data.append({
                                    "interface_name": iface_name,
                                    "score": 0,
                                    "severity": "CRITICAL",
                                    "trend_direction": "DOWN",
                                    "optical_score": -99.9,
                                    "tx_power": -99.9,
                                    "rx_power": -99.9,
                                    "temperature": 0,
                                    "description": f"{sfp_desc} - Down (no stats)",
                                })

                    if device_data:
                        all_data[device] = device_data

                    alert_panel.add_alert(f"    ✓ Processed {len(device_data)} carrier interface(s)", "success")

                except Exception as e:
                    alert_panel.add_alert(f"    ❌ Error: {str(e)}", "error")
                    import traceback
                    traceback.print_exc()

            # Update the panels with fetched data
            alert_panel.add_alert("", "info")
            alert_panel.add_alert("📊 Updating dashboard panels...", "info")

            if all_data:
                # Update network summary
                summary_panel = self.query_one("#network-summary", NetworkSummaryPanel)
                summary_panel.update_summary(all_data)

                scores_panel = self.query_one("#health-scores", HealthScoresPanel)
                scores_panel.update_scores(all_data)

                optics_panel = self.query_one("#optics-table", OpticalDiagnosticsPanel)
                optics_panel.update_optics(all_data)

                # Update details panel with the first interface from the first device
                details_panel = self.query_one("#interface-details", InterfaceDetailsPanel)
                first_device = list(all_data.keys())[0]
                if all_data[first_device]:
                    # Create a properly formatted interface data dict
                    first_iface = all_data[first_device][0]
                    details_data = {
                        "device": first_device,
                        "interface": first_iface.get("interface_name", "unknown"),
                        "score": first_iface.get("score", 0),
                        "severity": first_iface.get("severity", "INFO"),
                        "optical_score": first_iface.get("optical_score", 0),
                        "error_score": 0,  # Not available yet
                        "stability_score": 0,  # Not available yet
                        "tx_power": first_iface.get("tx_power", -99.9),
                        "rx_power": first_iface.get("rx_power", -99.9),
                        "temperature": first_iface.get("temperature", 0),
                        "description": first_iface.get("description", ""),
                        "errors": {}  # Not available yet
                    }
                    details_panel.update_details(details_data)

                # Add summary to alert history
                total_interfaces = sum(len(interfaces) for interfaces in all_data.values())
                alert_panel.add_alert(f"✓ Updated {total_interfaces} interface(s) across {len(all_data)} device(s)", "success")
            else:
                alert_panel.add_alert("⚠ No data to display", "warning")

            alert_panel.add_alert("", "info")
            alert_panel.add_alert("✓ Fetch complete!", "success")

            # Update header status after successful fetch
            header = self.app.query_one("#pulse-header", PulseHeader)
            header.update_status()

        except Exception as e:
            alert_panel.add_alert(f"❌ Fetch error: {str(e)}", "error")
            import traceback
            traceback.print_exc()

        finally:
            button.disabled = False
            button.label = "FETCH"


# ──────────────────────────────────────────────────────────────────────────────
# Panel Classes
# ──────────────────────────────────────────────────────────────────────────────

class HealthPanel(Vertical):
    """Base panel with border-title support.

    Styles are loaded from frontend/ui/styles/health_dashboard.tcss
    """

    def __init__(self, title: str, **kwargs):
        # Set border_title attribute after construction
        super().__init__(**kwargs)
        self.border_title = title

    def compose(self) -> ComposeResult:
        yield from self._compose_content()

    def _compose_content(self) -> ComposeResult:
        """Override this to provide panel content."""
        yield Container(id="content", classes="PanelContent")


class NetworkSummaryPanel(HealthPanel):
    """Panel 1: Network-wide summary statistics."""

    def __init__(self, **kwargs):
        super().__init__(title="Network Summary", **kwargs)

    def _compose_content(self) -> ComposeResult:
        """Compose network summary content."""
        with Vertical(id="content", classes="PanelContent"):
            yield Static("No data. Press 'FETCH' to load.", id="summary-placeholder")

    def update_summary(self, all_data: dict) -> None:
        """Update network summary with fetched data."""
        content = self.query_one("#content", Vertical)
        content.remove_children()

        # Calculate overall statistics
        total_devices = len(all_data)
        total_interfaces = sum(len(interfaces) for interfaces in all_data.values())

        # Count interfaces by status
        up_count = 0
        down_count = 0
        total_score = 0
        critical_count = 0

        for device, interfaces in all_data.items():
            for iface in interfaces:
                score = iface.get("score", 0)
                total_score += score

                if score == 0:
                    down_count += 1
                    critical_count += 1
                else:
                    up_count += 1

        avg_score = total_score / (total_interfaces) if total_interfaces > 0 else 0

        # Overall health
        overall_color = "#00ff00" if avg_score >= 80 else "#ffff00" if avg_score >= 50 else "#ff0000"
        overall_status = "HEALTHY" if avg_score >= 80 else "DEGRADED" if avg_score >= 50 else "CRITICAL"

        # Build summary text
        summary = f"""[{overall_color} bold]Network Overview[/]

[dim]Devices:[/] {total_devices}
[dim]Interfaces:[/] {total_interfaces}
[dim]Up:[/] [#00ff00]{up_count}[/]
[dim]Down:[/] [#ff0000]{down_count}[/]

[{overall_color} bold]Health Status[/]
[{overall_color}]{overall_status}[/]
[dim]Avg Score:[/] [{overall_color} bold]{avg_score:.0f}/100[/]

[dim]Critical:[/] [#ff0000]{critical_count}[/]"""
        content.mount(Static(summary))


class HealthScoresPanel(HealthPanel):
    """Panel 1: Health scores grouped by device."""

    def __init__(self, **kwargs):
        super().__init__(title="Health Scores", **kwargs)

    def _compose_content(self) -> ComposeResult:
        """Compose health scores content."""
        with Vertical(id="content", classes="PanelContent"):
            # Device groups will be dynamically added
            yield Static("No data. Press 'FETCH' to load.", id="scores-placeholder")

    def update_scores(self, device_scores: dict):
        """
        Update health scores grouped by device.

        Args:
            device_scores: Dict mapping device_name to list of interface scores
                         e.g., {"router1": [{"interface": "et-0/0/0", "score": 95, ...}]}
        """
        content = self.query_one("#content", Vertical)
        content.remove_children()

        # Calculate overall health statistics
        total_interfaces = sum(len(interfaces) for interfaces in device_scores.values())
        healthy_count = sum(
            1 for interfaces in device_scores.values()
            for iface in interfaces
            if iface.get("score", 0) >= 80
        )
        warning_count = sum(
            1 for interfaces in device_scores.values()
            for iface in interfaces
            if 50 <= iface.get("score", 0) < 80
        )
        critical_count = sum(
            1 for interfaces in device_scores.values()
            for iface in interfaces
            if iface.get("score", 0) < 50
        )

        # Calculate average score
        all_scores = [
            iface.get("score", 0)
            for interfaces in device_scores.values()
            for iface in interfaces
        ]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        # Overall health summary
        overall_color = "#00ff00" if avg_score >= 80 else "#ffff00" if avg_score >= 50 else "#ff0000"
        overall_status = "HEALTHY" if avg_score >= 80 else "DEGRADED" if avg_score >= 50 else "CRITICAL"

        # Summary section
        summary = f"""
[bold #ff8800]╔════════════════════════════════════════╗[/bold #ff8800]
[bold #ff8800]║[/bold #ff8800] [bold white]NETWORK HEALTH SUMMARY[/bold white]         [bold #ff8800]║[/bold #ff8800]
[bold #ff8800]╠════════════════════════════════════════╣[/bold #ff8800]
[bold #ff8800]║[/bold #ff8800] Status: [{overall_color} bold]{overall_status}[/{overall_color} bold]
[bold #ff8800]║[/bold #ff8800] Avg Score: [{overall_color} bold]{avg_score:.0f}/100[/{overall_color} bold]
[bold #ff8800]║[/bold #ff8800]
[bold #ff8800]║[/bold #ff8800] Total:    [white]{total_interfaces:>3}[/white] interfaces
[bold #ff8800]║[/bold #ff8800] [#00ff00]✓[/#00ff00] Healthy: [#00ff00]{healthy_count:>3}[/#00ff00]
[bold #ff8800]║[/bold #ff8800] [#ffff00]⚡[/#ffff00] Warning: [#ffff00]{warning_count:>3}[/#ffff00]
[bold #ff8800]║[/bold #ff8800] [#ff0000]⚠[/#ff0000] Critical: [#ff0000]{critical_count:>3}[/#ff0000]
[bold #ff8800]╚════════════════════════════════════════╝[/bold #ff8800]
"""
        content.mount(Static(summary))

        # Separator
        content.mount(Static(""))

        for device, interfaces in device_scores.items():
            # Calculate device average score
            device_scores_list = [iface.get("score", 0) for iface in interfaces]
            device_avg = sum(device_scores_list) / len(device_scores_list) if device_scores_list else 0

            # Device color based on average
            device_color = "#00ff00" if device_avg >= 80 else "#ffff00" if device_avg >= 50 else "#ff0000"
            device_status = "●" if device_avg >= 80 else "◐" if device_avg >= 50 else "○"

            # Device group header with stats
            header_text = f"[{device_color} bold]{device_status} {device}[/] [#888888]({len(interfaces)} circuits, avg: {device_avg:.0f})[/]"
            content.mount(Static(header_text, classes="DeviceGroup"))

            # Interface rows
            for iface_data in interfaces:
                iface_name = iface_data.get("interface_name", "unknown")
                score = iface_data.get("score", 0)
                severity = iface_data.get("severity", "INFO")
                trend = iface_data.get("trend_direction", "STABLE")

                # Replace slashes and dots in interface name for valid ID
                iface_id = iface_name.replace("/", "-").replace(".", "-")

                # Replace dots in device name (IP address) for valid ID
                device_id = device.replace(".", "-").replace(":", "-")

                # Create a compact row layout
                row_text = f"  "
                row_text += f"[#ff8800]{iface_name:<15}[/]"

                # Add health bar visualization
                if score >= 80:
                    bar_color = "#00ff00"
                elif score >= 50:
                    bar_color = "#ffff00"
                else:
                    bar_color = "#ff0000"

                filled = int(score / 10)
                bar = "█" * filled + "░" * (10 - filled)
                row_text += f" [{bar_color}]{bar}[/{bar_color}] "
                row_text += f"[{bar_color} bold]{score:>3.0f}%[/{bar_color} bold]"

                # Add trend arrow
                if trend == "IMPROVING":
                    row_text += " [#00ff00]↗[/#00ff00]"
                elif trend == "DEGRADING":
                    row_text += " [#ff0000]↘[/#ff0000]"
                elif trend == "DOWN":
                    row_text += " [#ff0000]✖[/#ff0000]"
                else:
                    row_text += " [#888888]→[/#888888]"

                content.mount(Static(row_text))

            # Add spacing between devices
            content.mount(Static(""))


class OpticalDiagnosticsPanel(HealthPanel):
    """Panel 2: Optical diagnostics table."""

    def __init__(self, **kwargs):
        super().__init__(title="Optical Diagnostics", **kwargs)

    def _compose_content(self) -> ComposeResult:
        with Vertical(id="content", classes="PanelContent"):
            table = OpticalMetricsTable(id="optics-table")
            yield table

    def update_optics(self, all_data: dict) -> None:
        """Update optical diagnostics with fetched data."""
        try:
            table = self.query_one("#optics-table", OpticalMetricsTable)

            # Build diagnostics dict for the table
            diagnostics = {}
            for device, interfaces in all_data.items():
                for iface_data in interfaces:
                    iface_name = iface_data.get("interface_name", "unknown")
                    key = f"{device}:{iface_name}"

                    diagnostics[key] = {
                        "laser_output_power": iface_data.get("tx_power", -99.9),
                        "rx_signal_power": iface_data.get("rx_power", -99.9),
                        "module_temperature": iface_data.get("temperature", 0),
                        "laser_bias_current": 0.0,  # Not available in current data
                    }

            table.update_from_diagnostics(diagnostics)
        except Exception as e:
            logger.error("optics_panel_update_failed", error=str(e))


class OpticalStatsPanel(HealthPanel):
    """Panel: Optical statistics and summary."""

    def __init__(self, **kwargs):
        super().__init__(title="Optical Statistics", **kwargs)

    def _compose_content(self) -> ComposeResult:
        """Compose optical statistics content."""
        with Vertical(id="content", classes="PanelContent"):
            yield Static("No data. Press 'FETCH' to load.", id="stats-placeholder")

    def update_stats(self, all_data: dict) -> None:
        """Update optical statistics with fetched data."""
        content = self.query_one("#content", Vertical)
        content.remove_children()

        # Calculate statistics
        interfaces_count = sum(len(interfaces) for interfaces in all_data.values())
        healthy_count = 0
        warning_count = 0
        critical_count = 0

        total_tx = 0
        total_rx = 0
        total_temp = 0
        valid_interfaces = 0

        for device, interfaces in all_data.items():
            for iface in interfaces:
                tx = iface.get("tx_power", -99.9)
                rx = iface.get("rx_power", -99.9)
                temp = iface.get("temperature", 0)

                if rx < -15 or rx > 0:
                    critical_count += 1
                elif rx < -12:
                    warning_count += 1
                else:
                    healthy_count += 1

                if tx > -50:  # Valid TX power
                    total_tx += tx
                    valid_interfaces += 1
                if rx > -50:  # Valid RX power
                    total_rx += rx
                if temp > 0:
                    total_temp += temp
                    valid_interfaces += 1

        # Calculate averages
        avg_tx = total_tx / valid_interfaces if valid_interfaces > 0 else 0
        avg_rx = total_rx / valid_interfaces if valid_interfaces > 0 else 0
        avg_temp = total_temp / valid_interfaces if valid_interfaces > 0 else 0

        # Build stats display
        stats = f"""[bold #ff8800]Optical Overview[/]

[dim]Total Interfaces:[/] {interfaces_count}
[dim]Healthy:[/] [#00ff00]{healthy_count}[/]
[dim]Warning:[/] [#ffff00]{warning_count}[/]
[dim]Critical:[/] [#ff0000]{critical_count}[/]

[bold white]Averages[/]
[dim]TX Power:[/] [{self._get_power_color(avg_tx)}]{avg_tx:.2f} dBm[/]
[dim]RX Power:[/] [{self._get_power_color(avg_rx)}]{avg_rx:.2f} dBm[/]
[dim]Temperature:[/] [{self._get_temp_color(avg_temp)}]{avg_temp:.1f} °C[/]"""
        content.mount(Static(stats))

    def _get_power_color(self, power: float) -> str:
        """Get color for power level."""
        if power < -15 or power > 0:
            return "#ff0000"
        elif power < -12:
            return "#ffff00"
        else:
            return "#00ff00"

    def _get_temp_color(self, temp: float) -> str:
        """Get color for temperature."""
        if temp > 70:
            return "#ff0000"
        elif temp > 60:
            return "#ffff00"
        else:
            return "#00ff00"


class InterfaceDetailsPanel(HealthPanel):
    """Panel 3: Detailed interface information."""

    def __init__(self, **kwargs):
        super().__init__(title="Interface Details", **kwargs)

    def _compose_content(self) -> ComposeResult:
        with Vertical(id="content", classes="PanelContent"):
            # Placeholder message (hidden when data is loaded)
            yield Static(
                "Select an interface to view details",
                id="details-placeholder"
            )
            # Content wrapper (hidden initially)
            with Vertical(id="details-content", classes="hidden"):
                yield Static("", id="details-interface")
                yield Static("", id="details-scores")
                yield Static("", id="details-errors")
                yield TrendIndicator(id="details-trend")

    def update_details(self, interface_data: dict):
        """Update the details panel with interface information."""
        # Hide placeholder and show content using CSS classes
        placeholder = self.query_one("#details-placeholder", Static)
        placeholder.add_class("hidden")

        content = self.query_one("#details-content", Vertical)
        content.remove_class("hidden")

        # Update interface name
        iface_label = self.query_one("#details-interface", Static)
        device = interface_data.get("device", "unknown")
        iface = interface_data.get("interface", "unknown")
        severity = interface_data.get("severity", "INFO")
        score = interface_data.get("score", 0)

        color_map = {
            "INFO": "green",
            "WARNING": "yellow",
            "CRITICAL": "red"
        }
        color = color_map.get(severity, "white")

        iface_label.update(f"[{color} bold]{device}:{iface}[/] - Score: {score:.0f}/100")

        # Update component scores
        scores_label = self.query_one("#details-scores", Static)
        optical = interface_data.get("optical_score", 0)
        errors = interface_data.get("error_score", 0)
        stability = interface_data.get("stability_score", 0)

        scores_label.update(
            f"Optical: {optical:.0f}%  |  Errors: {errors:.0f}%  |  Stability: {stability:.0f}%"
        )

        # Update error info
        errors_label = self.query_one("#details-errors", Static)
        err_data = interface_data.get("errors", {})
        if err_data:
            input_err = err_data.get("input_errors", 0)
            output_err = err_data.get("output_errors", 0)
            crc_err = err_data.get("input_crc_errors", 0) + err_data.get("output_crc_errors", 0)
            drops = err_data.get("input_drops", 0) + err_data.get("output_drops", 0)
            carrier = err_data.get("carrier_transitions", 0)

            errors_label.update(
                f"Errors: {input_err} in / {output_err} out  |  CRC: {crc_err}  |  "
                f"Drops: {drops}  |  Carrier Trans: {carrier}"
            )
        else:
            # Show description instead when no error data
            description = interface_data.get("description", "")
            if description:
                errors_label.update(f"SFP: {description}")
            else:
                errors_label.update("")

        # Update trend
        trend_widget = self.query_one("#details-trend", TrendIndicator)
        trend_widget.update_from_score(interface_data)


class AlertHistoryPanel(HealthPanel):
    """Panel 4: Alert history log."""

    def __init__(self, **kwargs):
        super().__init__(title="Alert History", **kwargs)

    def _compose_content(self) -> ComposeResult:
        from frontend.ui.widgets.pulse_widgets import CompactLog
        with Vertical(id="content", classes="PanelContent"):
            yield CompactLog(
                max_entries=100,
                show_timestamps=True,
                id="alert-log"
            )

    def add_alert(self, message: str, severity: str = "info"):
        """Add an alert to the history log."""
        log = self.query_one("#alert-log", CompactLog)

        # Map severity to log kind
        kind_map = {
            "INFO": "info",
            "WARNING": "warning",
            "CRITICAL": "error",
            "ERROR": "error"
        }

        log.add_log(message, kind=kind_map.get(severity, "info"))
