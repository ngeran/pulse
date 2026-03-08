from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Log, Label
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from backend.core.connection_engine import ConnectionManager
from backend.core.interface_discovery import InterfaceDiscovery
from backend.core.logic_engine import HealthScoringEngine
from backend.core.events import ConnectionEvent, HealthEvent, EventMessage
from backend.config.loader import load_config
from backend.utils.logging import setup_logging, logger
from frontend.ui.screens.connection import ConnectionScreen
from backend.api.server import run_server, start_event_broadcaster
import asyncio
import threading

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
    """Critical alerts panel at the top of UI"""
    
    def on_mount(self):
        self.update("NO SPOF DETECTED")
        self.styles.background = "green"
        self.styles.color = "white"

class PulseApp(App):
    CSS_PATH = "styles/dark.tcss"
    
    BINDINGS = [
        ("c", "push_connection", "Connect"),
        ("d", "disconnect_selected", "Disconnect"),
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
        self.ws_connected = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield BackendStatus(id="ws-status")
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
        self.log_backend_event("[INFO] App initialization complete. Press 'c' to connect a device.")

    async def start_backend(self):
        """Starts the FastAPI/WebSocket server in a background task."""
        logger.info("backend_startup_beginning")

        # Attach the broadcaster to the connection manager
        await start_event_broadcaster(self.conn_mgr)
        
        
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

        # Wait for server to start before connecting the client
        await asyncio.sleep(1)

        # Start the health check WS client loop in the background
        asyncio.create_task(self.ws_client_loop())

    async def ws_client_loop(self):
        """Maintains a persistent WebSocket connection to the backend to track its health."""
        import websockets
        uri = "ws://localhost:8001/ws/events"
        while True:
            logger.info("ws_client_connecting", uri=uri)
            self.log_backend_event(f"[INFO] Attempting to connect to backend at {uri}...")
            try:
                async with websockets.connect(uri, ping_interval=10, ping_timeout=10, close_timeout=1) as websocket:
                    logger.info("ws_client_connected")
                    self.set_ws_status(True)
                    self.log_backend_event("[SUCCESS] Connected to Backend WebSocket.")

                    # Send periodic keepalive and listen for messages
                    async def keepalive():
                        while True:
                            await asyncio.sleep(5)
                            try:
                                await websocket.send('{"type":"ping"}')
                            except Exception:
                                break

                    keepalive_task = asyncio.create_task(keepalive())

                    try:
                        # Listen for messages from server
                        async for msg in websocket:
                            # Handle server events
                            logger.debug("ws_client_message", message=msg)
                            await self.handle_ws_message(msg)
                    finally:
                        keepalive_task.cancel()
            except Exception as e:
                logger.error("ws_client_error", error=str(e))
                self.log_backend_event(f"[ERROR] WS Connection failed: {e}")

            self.set_ws_status(False)
            self.log_backend_event("[WARN] Retrying backend connection in 2 seconds...")
            await asyncio.sleep(2)  # Reconnect backoff

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

    async def handle_ws_message(self, msg: str):
        """Handle WebSocket messages from backend."""
        import json
        try:
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "health_update":
                # Update health dashboard
                device = data.get("device")
                event_data = data.get("data", {})
                self.update_health_dashboard(device, event_data)

                # Log to event log
                log = self.query_one("#event-log", EventLog)
                event_type = data.get("event_type", "health_update")
                interface = event_data.get("interface", "unknown")
                score_data = event_data.get("score", {})
                score = score_data.get("score", 0) if score_data else 0
                log.write_line(f"[{event_type}] {device}: {interface} - Score: {score:.0f}/100")

            elif msg_type == "circuit_sick":
                log = self.query_one("#event-log", EventLog)
                device = data.get("device")
                interface = data.get("interface", "unknown")
                log.write_line(f"[WARNING] {device}: {interface} - Circuit degraded")
                self.update_health_dashboard(device, data.get("score", {}))

            elif msg_type == "circuit_dead":
                log = self.query_one("#event-log", EventLog)
                device = data.get("device")
                interface = data.get("interface", "unknown")
                log.write_line(f"[CRITICAL] {device}: {interface} - Circuit failed")
                self.update_health_dashboard(device, data.get("score", {}))

        except json.JSONDecodeError:
            logger.warning("ws_client_invalid_json", message=msg[:100])
        except Exception as e:
            logger.error("ws_client_handle_error", error=str(e))

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
        if not getattr(self, "ws_connected", False):
            log = self.query_one("#event-log", EventLog)
            log.write_line("[ERROR] Cannot connect: Wait for Backend WS to establish connection.")
            return

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
        if not getattr(self, "ws_connected", False):
            log = self.query_one("#event-log", EventLog)
            log.write_line("[ERROR] Cannot disconnect: Backend WS is not connected.")
            return
            
        tree = self.query_one("#device-tree", DeviceTree)
        if tree.cursor_node and tree.cursor_node.data:
            host = tree.cursor_node.data
            asyncio.create_task(self.conn_mgr.disconnect_device(host))

if __name__ == "__main__":
    app = PulseApp()
    app.run()
