from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Set, Optional
import asyncio
import json
from backend.core.connection_engine import ConnectionManager
from backend.core.events import ConnectionEvent, HealthEvent, EventMessage
from backend.utils.logging import logger

app = FastAPI(title="Pulse API")

class ConnectionManagerWS:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._connection_id = 0

    async def connect(self, websocket: WebSocket) -> int:
        await websocket.accept()
        self.active_connections.add(websocket)
        self._connection_id += 1
        conn_id = self._connection_id
        logger.info("ws_server_client_connected",
                   connection_id=conn_id,
                   active_connections=len(self.active_connections))
        return conn_id

    def disconnect(self, websocket: WebSocket, conn_id: int = None):
        self.active_connections.discard(websocket)
        logger.info("ws_server_client_disconnected",
                   connection_id=conn_id,
                   active_connections=len(self.active_connections))

    async def broadcast(self, message: str):
        if not self.active_connections:
            logger.debug("ws_server_broadcast_skipped", reason="no_connections")
            return

        logger.debug("ws_server_broadcast",
                    message=message[:100] if len(message) > 100 else message,
                    recipients=len(self.active_connections))

        # Send to all connections, handling any failures
        failed = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning("ws_server_send_failed", error=str(e))
                failed.append(connection)

        # Remove failed connections
        for conn in failed:
            self.active_connections.discard(conn)

ws_manager = ConnectionManagerWS()


async def start_websocket_server(ws_manager: ConnectionManagerWS, port: int = 8001):
    """
    Start the WebSocket server for event broadcasting.

    Args:
        ws_manager: WebSocket connection manager
        port: WebSocket port to listen on

    Note:
        This is now managed by the MessageEngine - this function is kept for compatibility
        but the MessageEngine handles the actual WebSocket lifecycle.
    """
    # The WebSocket endpoint is already defined below
    # This function is now a no-op since MessageEngine manages the server
    logger.info("websocket_server_managed_by_message_engine", port=port)


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    conn_id = await ws_manager.connect(websocket)
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info("ws_server_connection_established", client=client_host, connection_id=conn_id)

    try:
        message_count = 0
        while True:
            # Keep connection open - receive with timeout to allow ping/pong
            try:
                # Use a short timeout to handle pings properly
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                message_count += 1
                logger.debug("ws_server_message_received",
                           connection_id=conn_id,
                           message_count=message_count,
                           data=data[:50] if len(data) > 50 else data)
            except asyncio.TimeoutError:
                # Timeout is expected - allows ping/pong to work
                continue
    except WebSocketDisconnect as e:
        logger.info("ws_server_disconnected",
                   connection_id=conn_id,
                   code=e.code,
                   reason=e.reason if e.reason else "no_reason")
        ws_manager.disconnect(websocket, conn_id)
    except Exception as e:
        logger.error("ws_server_error",
                    connection_id=conn_id,
                    error_type=type(e).__name__,
                    error=str(e))
        ws_manager.disconnect(websocket, conn_id)

async def start_event_broadcaster(conn_mgr: ConnectionManager, health_engine: Optional[Any] = None):
    """
    Subscribes to ConnectionManager and HealthEngine events and broadcasts them to all
    connected WebSocket clients.
    """
    async def event_handler(event: EventMessage):
        logger.debug("event_broadcaster_received",
                    event_type=event.event_type.value,
                    device=event.device_name)

        if event.event_type == ConnectionEvent.PROGRESS:
            data = {
                "type": "progress",
                "device": event.device_name,
                "message": event.data.get("message") if event.data else ""
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type == ConnectionEvent.CONNECTED:
            data = {
                "type": "connected",
                "device": event.device_name
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type == ConnectionEvent.DISCONNECTED:
            data = {
                "type": "disconnected",
                "device": event.device_name
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type == ConnectionEvent.ERROR:
            data = {
                "type": "error",
                "device": event.device_name,
                "attempt": event.data.get("attempt") if event.data else 1
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type in (HealthEvent.HEALTH_CHANGED, HealthEvent.HEALTH_ALERT, HealthEvent.TREND_DETECTED):
            # Broadcast health score updates
            data = {
                "type": "health_update",
                "device": event.device_name,
                "event_type": event.event_type.value,
                "data": event.data
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type == HealthEvent.CIRCUIT_SICK:
            data = {
                "type": "circuit_sick",
                "device": event.device_name,
                "interface": event.data.get("interface") if event.data else "",
                "score": event.data.get("score") if event.data else {}
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type == HealthEvent.CIRCUIT_DEAD:
            data = {
                "type": "circuit_dead",
                "device": event.device_name,
                "interface": event.data.get("interface") if event.data else "",
                "score": event.data.get("score") if event.data else {}
            }
            await ws_manager.broadcast(json.dumps(data))
        elif event.event_type == HealthEvent.SPOF_DETECTED:
            data = {
                "type": "spof_detected",
                "device": event.device_name,
                "data": event.data
            }
            await ws_manager.broadcast(json.dumps(data))

    await conn_mgr.subscribe_to_events(event_handler)

    # Also subscribe to health engine events if provided
    if health_engine:
        await health_engine.subscribe_to_events(event_handler)
        logger.info("api_health_broadcaster_started")

    logger.info("api_broadcaster_started")

def run_server(conn_mgr: ConnectionManager, port: int = 8000):
    import uvicorn

    logger.info("api_server_configuring", port=port, host="0.0.0.0")

    # We need to start the broadcaster before the server starts
    # But since uvicorn.run is blocking, we manage this in the app integration
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    return server
