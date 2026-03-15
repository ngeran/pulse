from textual.app import App, ComposeResult
from backend.core.connection_engine import ConnectionManager
from backend.core.interface_discovery import InterfaceDiscovery
from backend.core.logic_engine import HealthScoringEngine
from backend.core.device_manager import DeviceManager
from backend.core.fetch_engine import FetchEngine
from backend.config.loader import load_config
from backend.utils.logging import setup_logging, logger
from frontend.ui.screens.connection import ConnectionScreen
from frontend.ui.screens.device_management import DeviceManagementScreen
from frontend.ui.screens.dashboard import DashboardScreen
from frontend.ui.screens.fetch_results import FetchResultsScreen
from frontend.ui.screens.prism import PrismScreen
from frontend.ui.screens.help_screen import HelpScreen
import asyncio
from typing import Optional, Any

class PulseApp(App):
    CSS_PATH = "../styles/dark.tcss"

    BINDINGS = [
        ("b", "push_dashboard", "Dashboard"),
        ("h", "show_help", "Help"),
        ("m", "push_device_management", "Device Management"),
        ("p", "push_prism", "PRISM"),
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
        self.fetch_engine = FetchEngine(self.conn_mgr)  # Initialize fetch engine
        self.message_engine = None  # Will be initialized in start_backend()
        self.ws_connected = False  # WebSocket connection status
        self.backend_ready = False  # Backend server ready status

    def compose(self) -> ComposeResult:
        """Compose the app (base screen, not used since we push to Dashboard)."""
        # Each screen has its own modular footer
        # Yield a placeholder widget that will be replaced when we push screens
        from textual.widgets import Static
        yield Static(id="app-placeholder")


    async def on_mount(self) -> None:
        """Initialize the application when mounted."""
        logger.info("app_mounting", app_name="PulseApp")
        self.install_screen(ConnectionScreen(), name="connection")
        self.install_screen(DashboardScreen(), name="dashboard")
        self.install_screen(DeviceManagementScreen(), name="device_management")
        self.install_screen(PrismScreen(), name="prism")
        self.install_screen(HelpScreen(), name="help")
        # FetchResultsScreen doesn't need to be pre-installed, it's created dynamically
        # Enable console logging for visibility
        setup_logging(console_output=True)
        logger.info("app_logging_initialized", console_enabled=True)

        # Start Backend Server
        logger.info("app_starting_backend")
        asyncio.create_task(self.start_backend())
        logger.info("app_mounted_successfully")

        # Push Dashboard screen immediately
        self.push_screen("dashboard")

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

        # Register fetch engine with API server
        from backend.api.server import set_fetch_engine
        set_fetch_engine(self.fetch_engine)
        logger.info("fetch_engine_registered")

        logger.info("backend_starting", port=8001)

        # We use uvicorn to run the FastAPI app
        import uvicorn
        from backend.api.server import app

        config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="warning")
        server = uvicorn.Server(config)

        # We run the server in a separate task
        async def run_uvicorn():
            try:
                await server.serve()
            except BaseException as e:
                import traceback
                tb = traceback.format_exc()
                logger.error("backend_server_crashed", error_type=type(e).__name__, error=str(e), traceback=tb[:500])

        asyncio.create_task(run_uvicorn())

        # Wait for server to start
        await asyncio.sleep(1)

        # Test WebSocket connection to verify backend is ready
        await self._test_websocket_connection()

        logger.info("app_ready")

    async def _test_websocket_connection(self):
        """Test WebSocket connection to verify backend is ready."""
        import websockets
        uri = "ws://localhost:8001/ws/events"

        try:
            async with websockets.connect(uri, ping_interval=10, ping_timeout=10, close_timeout=1) as websocket:
                logger.info("websocket_test_success")
                self.backend_ready = True
                self.ws_connected = True
                logger.info("backend_status_update", backend_ready=True, ws_connected=True)
        except Exception as e:
            logger.error("websocket_test_failed", error=str(e))
            # Retry after a short delay
            await asyncio.sleep(0.5)
            try:
                async with websockets.connect(uri, ping_interval=10, ping_timeout=10, close_timeout=1) as websocket:
                    logger.info("websocket_test_retry_success")
                    self.backend_ready = True
                    self.ws_connected = True
                    logger.info("backend_status_update", backend_ready=True, ws_connected=True)
            except Exception as e2:
                logger.error("websocket_test_retry_failed", error=str(e2))
                self.backend_ready = True
                self.ws_connected = False
                logger.info("backend_status_update", backend_ready=True, ws_connected=False)

    async def action_push_connection(self) -> None:
        def handle_result(result):
            if result:
                asyncio.create_task(self.connect_to_new_devices(result))

        self.push_screen(ConnectionScreen(), handle_result)

    async def connect_to_new_devices(self, data: dict):
        hosts = data["hosts"]
        username = data["username"]
        password = data["password"]

        logger.info("connection_initiated", hosts=hosts, username=username)
        print(f"[DEBUG] Connecting to {len(hosts)} devices: {hosts}")

        for host in hosts:
            logger.info("connection_starting", device=host, username=username)
            print(f"[DEBUG] Starting connection to {host}")
            asyncio.create_task(self.conn_mgr.connect_device(host, username, password))

    async def action_disconnect_selected(self) -> None:
        """Disconnect all devices (since we no longer have a device tree)."""
        for host in list(self.conn_mgr.sessions.keys()):
            asyncio.create_task(self.conn_mgr.disconnect_device(host))

    def action_push_device_management(self) -> None:
        """Action to push the device management screen."""
        self.push_screen("device_management")

    def action_push_dashboard(self) -> None:
        """Action to push the dashboard screen."""
        self.push_screen("dashboard")

    def action_push_prism(self) -> None:
        """Action to push the PRISM screen."""
        self.push_screen("prism")

    def action_show_help(self) -> None:
        """Action to show the help screen."""
        self.push_screen("help")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def get_message_engine(self) -> Optional[Any]:
        """Get the MessageEngine instance (if initialized)."""
        return getattr(self, 'message_engine', None)

if __name__ == "__main__":
    app = PulseApp()
    app.run()
