from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Log, Label
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from backend.core.connection_engine import ConnectionManager
from backend.core.interface_discovery import InterfaceDiscovery
from backend.core.logic_engine import HealthScoringEngine
from backend.core.device_manager import DeviceManager
from backend.core.events import ConnectionEvent, HealthEvent, EventMessage
from backend.config.loader import load_config
from backend.utils.logging import setup_logging, logger
from frontend.ui.screens.connection import ConnectionScreen
from frontend.ui.screens.health_dashboard import HealthDashboardScreen
from frontend.ui.screens.realtime_dashboard import RealtimeDashboardScreen
from frontend.ui.screens.device_management import DeviceManagementScreen
from frontend.ui.widgets.pulse_header import PulseHeader
import asyncio
import threading
from typing import Optional, Any

class DeviceTree(Tree):
    """Tree view of all devices and interfaces"""
    pass

class HealthDashboard(Static):
    """Real-time health metrics with color coding"""
    pass

class EventLog(Log):
    """Scrollable log of system events and alerts"""
    pass

class BackendStatus(Label):
    """Status indicator for the FastAPI/WebSocket backend."""
    def on_mount(self):
        self.update("WS: DISCONNECTED")
        self.add_class("status-disconnected")

class SPOFAlertPanel(Static):
    """Critical alerts panel at the top of UI - Single Point of Failure detection"""

    def on_mount(self):
        self.update("NO SPOF DETECTED")

class PulseApp(App):
    CSS_PATH = "../styles/dark.tcss"

    BINDINGS = [
        ("c", "push_connection", "Connect"),
        ("d", "disconnect_selected", "Disconnect"),
        ("h", "push_health_dashboard", "Health Dashboard"),
        ("r", "push_realtime_dashboard", "Realtime Dashboard"),
        ("m", "push_device_management", "Device Management"),
        ("q", "quit", "Quit")
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = load_config()
        self.conn_mgr = ConnectionManager(
            max_sessions=self.config.polling_interval,
            retry_limit=self.config.retry_attempts
        )
        self.discovery = InterfaceDiscovery(self.conn_mgr, cache_ttl=self.config.cache_ttl)
        self.health_engine = HealthScoringEngine(self.conn_mgr, self.config)
        self.device_manager = DeviceManager(self.conn_mgr)
        self.ws_connected = False
        self.message_engine = None  # Will be initialized in start_backend()

    def compose(self) -> ComposeResult:
        yield PulseHeader(id="pulse-header")
        yield SPOFAlertPanel(id="spof-alert")
        with Horizontal():
            yield DeviceTree("Devices", id="device-tree")
            with Vertical():
                yield HealthDashboard("Health Dashboard", id="health-dash")
                yield EventLog(id="event-log")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application when mounted."""
        logger.info("app_mounting", app_name="PulseApp")
        self.install_screen(ConnectionScreen(), name="connection")
        self.install_screen(HealthDashboardScreen(), name="health_dashboard")
        self.install_screen(RealtimeDashboardScreen(), name="realtime_dashboard")
        self.install_screen(DeviceManagementScreen(), name="device_management")
        # Enable console logging for visibility
        setup_logging(console_output=True)
        logger.info("app_logging_initialized", console_enabled=True)

        # Log startup message to UI
        self.log_backend_event("[INFO] Pulse App is starting...")

        # Subscribe to backend events
        await self.conn_mgr.subscribe_to_events(self.handle_connection_event)
        await self.health_engine.subscribe_to_events(self.handle_health_event)
        logger.info("app_events_subscribed")

        # Start Backend Server
        logger.info("app_starting_backend")
        self.log_backend_event("[INFO] Starting backend server on port 8001...")
        asyncio.create_task(self.start_backend())
        logger.info("app_mounted_successfully")
        self.log_backend_event("[INFO] App initialization complete. Press 'c' to connect a device, 'h' for health dashboard.")

    async def start_backend(self):
        """Starts the FastAPI/WebSocket server in a background task."""
        logger.info("backend_startup_beginning")

        # Initialize and start the MessageEngine
        from backend.core.message_engine import MessageEngine

        self.message_engine = MessageEngine(
            conn_mgr=self.conn_mgr,
            health_engine=self.health_engine,
            ws_port=8001,
            enable_aggregation=True,
            aggregation_window=1.0,
            aggregation_size=10
        )

        await self.message_engine.start()
        logger.info("message_engine_initialized")

        logger.info("backend_starting", port=8001)

        # We use uvicorn to run the FastAPI app
        import uvicorn
        from backend.api.server import app

        config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="debug")
        server = uvicorn.Server(config)

        # We run the server in a separate task
        async def run_uvicorn():
            try:
                await server.serve()
            except BaseException as e:
                import traceback
                tb = traceback.format_exc()
                logger.error("backend_server_crashed", error_type=type(e).__name__, error=str(e), traceback=tb[:500])
                self.log_backend_event(f"[ERROR] Backend Server crashed: {type(e).__name__}: {e}")
                
        asyncio.create_task(run_uvicorn())

        # Wait for server to start before marking as ready
        await asyncio.sleep(1)
        logger.info("app_ready")

        # Set backend as connected (no need for WebSocket client loop)
        self.set_ws_status(True)
        self.log_backend_event("[SUCCESS] Backend server started on port 8001")

    def log_backend_event(self, msg: str):
        try:
            log = self.query_one("#event-log", EventLog)
            log.write_line(msg)
        except Exception:
            pass

    def set_ws_status(self, connected: bool):
        """Updates the status widget based on connectivity."""
        self.ws_connected = connected
        try:
            status_widget = self.query_one("#ws-status", BackendStatus)
            if connected:
                status_widget.update("WS: CONNECTED")
                status_widget.remove_class("status-disconnected")
                status_widget.add_class("status-connected")
            else:
                status_widget.update("WS: DISCONNECTED")
                status_widget.remove_class("status-connected")
                status_widget.add_class("status-disconnected")
        except Exception:
            pass

    async def handle_connection_event(self, event: EventMessage):
        log = self.query_one("#event-log", EventLog)
        
        if event.event_type == ConnectionEvent.PROGRESS:
            msg = event.data.get("message") if event.data else ""
            log.write_line(f"[PROGRESS] {event.device_name}: {msg}")
        elif event.event_type == ConnectionEvent.CONNECTED:
            log.write_line(f"[CONNECTED] {event.device_name}")
            self.update_device_tree()
        elif event.event_type == ConnectionEvent.DISCONNECTED:
            log.write_line(f"[DISCONNECTED] {event.device_name}")
            self.update_device_tree()
        else:
            log.write_line(f"[{event.event_type.value.upper()}] {event.device_name}")

    def update_device_tree(self):
        """Refreshes the DeviceTree with current session information."""
        tree = self.query_one("#device-tree", DeviceTree)
        
        selected_data = tree.cursor_node.data if tree.cursor_node else None
        tree.clear()
        
        # Re-add existing nodes
        for host, session in self.conn_mgr.sessions.items():
            status_color = "green" if session.state.value == "CONNECTED" else "red"
            label = f"{host} [{session.state.value}]"
            tree.root.add_leaf(label, data=host)
        
        tree.root.expand()
        
        # Attempt to restore cursor
        if selected_data:
            for node in tree.root.children:
                if getattr(node, "data", None) == selected_data:
                    try:
                        tree.cursor_node = node
                    except Exception:
                        pass
                    break

    async def handle_health_event(self, event: EventMessage):
        log = self.query_one("#event-log", EventLog)
        log.write_line(f"[{event.event_type.value}] {event.device_name}: {event.data}")

        if event.event_type == HealthEvent.SPOF_DETECTED:
            alert = self.query_one("#spof-alert", SPOFAlertPanel)
            alert.update(f"SPOF DETECTED AT {event.device_name.upper()}!")
            alert.styles.background = "red"
            alert.styles.visibility = "visible"
        elif event.event_type in (HealthEvent.HEALTH_CHANGED, HealthEvent.HEALTH_ALERT, HealthEvent.TREND_DETECTED):
            # Update health dashboard with new score
            self.update_health_dashboard(event.device_name, event.data)

    def update_health_dashboard(self, device: str, data: dict):
        """Update the health dashboard with new score data."""
        try:
            dashboard = self.query_one("#health-dash", HealthDashboard)
            score_data = data.get("new_score") or data.get("score") or data

            if score_data and isinstance(score_data, dict):
                score = score_data.get("score", 0)
                severity = score_data.get("severity", "INFO")
                interface = score_data.get("interface_name", data.get("interface", "unknown"))

                # Build display string
                severity_colors = {
                    "INFO": "green",
                    "WARNING": "yellow",
                    "CRITICAL": "red"
                }
                color = severity_colors.get(severity, "white")

                trend = score_data.get("trend_direction", "STABLE")
                trend_icons = {
                    "IMPROVING": "↗",
                    "STABLE": "→",
                    "DEGRADING": "↘"
                }
                trend_icon = trend_icons.get(trend, "→")

                dashboard_text = f"[{color}]●[/] {device}:{interface} {score:.0f}/100 {trend_icon}"
                dashboard.update(dashboard_text)

        except Exception as e:
            logger.error("dashboard_update_error", error=str(e))

    async def action_push_connection(self) -> None:
        def handle_result(result):
            if result:
                asyncio.create_task(self.connect_to_new_devices(result))

        self.push_screen(ConnectionScreen(), handle_result)

    async def connect_to_new_devices(self, data: dict):
        hosts = data["hosts"]
        username = data["username"]
        password = data["password"]
        
        log = self.query_one("#event-log", EventLog)
        log.write_line(f"[INFO] Initiating connection to {len(hosts)} devices...")
        
        for host in hosts:
            # We add a temporary node for progress
            tree = self.query_one("#device-tree", DeviceTree)
            tree.root.add_leaf(f"{host} [CONNECTING]", data=host)
            asyncio.create_task(self.conn_mgr.connect_device(host, username, password))

    async def action_disconnect_selected(self) -> None:
        """Action to disconnect the currently selected device in the tree."""
        tree = self.query_one("#device-tree", DeviceTree)
        if tree.cursor_node and tree.cursor_node.data:
            host = tree.cursor_node.data
            asyncio.create_task(self.conn_mgr.disconnect_device(host))

    def action_push_health_dashboard(self) -> None:
        """Action to push the health dashboard screen."""
        self.push_screen("health_dashboard")

    def action_push_realtime_dashboard(self) -> None:
        """Action to push the realtime dashboard screen."""
        self.push_screen("realtime_dashboard")

    def action_push_device_management(self) -> None:
        """Action to push the device management screen."""
        self.push_screen("device_management")

    def get_message_engine(self) -> Optional[Any]:
        """Get the MessageEngine instance (if initialized)."""
        return getattr(self, 'message_engine', None)

if __name__ == "__main__":
    app = PulseApp()
    app.run()
