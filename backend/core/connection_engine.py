import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, ProbeError
from backend.core.events import ConnectionEvent, EventMessage
from backend.utils.logging import logger

class ConnectionState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    FAILED = "FAILED"

class DeviceSession:
    def __init__(self, host: str, user: str, password: Optional[str] = None, port: int = 22):
        self.host = host
        self.dev = Device(host=host, user=user, password=password, port=port)
        self.state = ConnectionState.DISCONNECTED
        self.last_heartbeat: float = 0
        self.retry_count = 0

    async def connect(self, progress_callback: Optional[Callable[[str], Any]] = None) -> bool:
        self.state = ConnectionState.CONNECTING
        try:
            if progress_callback:
                progress_callback("Initializing PyEZ Device")
            
            # PyEZ connect is blocking, run in executor
            loop = asyncio.get_event_loop()
            
            if progress_callback:
                progress_callback("Opening NETCONF session (SSH)")
                
            await loop.run_in_executor(None, self.dev.open)
            
            if progress_callback:
                progress_callback("Gathering device facts")
            
            self.state = ConnectionState.CONNECTED
            self.last_heartbeat = time.time()
            self.retry_count = 0
            
            if progress_callback:
                progress_callback("Connected successfully")
                
            return True
        except Exception as e:
            logger.error("connection_failed", device=self.host, error=str(e))
            self.state = ConnectionState.FAILED
            if progress_callback:
                progress_callback(f"Connection failed: {str(e)}")
            return False

    async def close(self):
        if hasattr(self, 'dev') and self.dev and getattr(self.dev, 'connected', False):
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.dev.close)
            except Exception as e:
                logger.error("close_session_error", error=str(e), device=self.host)
        self.state = ConnectionState.DISCONNECTED

    async def is_alive(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            # simple facts check or probe as heartbeat
            await loop.run_in_executor(None, lambda: self.dev.connected)
            return self.dev.connected
        except Exception:
            return False

    async def rpc(self, command: str) -> Optional[Dict]:
        """
        Execute an RPC command and return JSON response.

        Args:
            command: RPC command string (e.g., "show interfaces diagnostics optics ge-0/0/0 | display json")

        Returns:
            Parsed JSON response as dict, or None if command fails
        """
        if not self.dev.connected:
            logger.warning("rpc_not_connected", device=self.host, command=command)
            return None

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.dev.rpc(command))
            if result:
                # Convert PyEZ RPC response to dict
                return self._rpc_to_dict(result)
            return None
        except Exception as e:
            logger.error("rpc_failed", device=self.host, command=command, error=str(e))
            return None

    async def cli(self, command: str) -> Optional[Dict]:
        """
        Execute a CLI command and return JSON response.

        Use this for commands with '| display json' suffix.

        Args:
            command: CLI command string (e.g., "show interfaces diagnostics optics ge-0/0/0 | display json")

        Returns:
            Parsed JSON response as dict, or None if command fails
        """
        if not self.dev.connected:
            logger.warning("cli_not_connected", device=self.host, command=command)
            return None

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.dev.cli(command, format='json'))
            if result:
                # PyEZ cli() with format='json' already returns a dict
                if isinstance(result, dict):
                    return result
                else:
                    logger.warning("cli_unexpected_result_type", device=self.host, command=command, result_type=str(type(result)))
                    return None
            return None
        except Exception as e:
            logger.error("cli_failed", device=self.host, command=command, error=str(e))
            return None

    def _rpc_to_dict(self, rpc_result) -> Dict:
        """
        Convert PyEZ RPC result to dictionary.

        Args:
            rpc_result: PyEZ RPC response object

        Returns:
            Dictionary representation of the RPC response
        """
        if hasattr(rpc_result, 'todict'):
            return rpc_result.todict()
        elif hasattr(rpc_result, 'getfield'):
            # Handle lxml _Element objects
            from lxml import etree
            if isinstance(rpc_result, etree._Element):
                # Try to convert element to dict
                try:
                    # For XML elements, convert to string then parse
                    xml_str = etree.tostring(rpc_result, encoding='unicode')
                    import xmltodict
                    return xmltodict.parse(xml_str)
                except Exception as e:
                    logger.error("rpc_xml_parse_failed", error=str(e))
                    # Return raw XML as fallback
                    return {"_raw_xml": xml_str}
        elif isinstance(rpc_result, str):
            # Already a string, try to parse as JSON
            try:
                import json
                return json.loads(rpc_result)
            except Exception:
                return {"_raw_string": rpc_result}
        elif rpc_result is None:
            return {}

        logger.warning("rpc_unknown_result_type", result_type=str(type(rpc_result)))
        return {}


class ConnectionManager:
    def __init__(self, max_sessions: int = 10, retry_limit: int = 3):
        self.max_sessions = max_sessions
        self.retry_limit = retry_limit
        self.sessions: Dict[str, DeviceSession] = {}
        self.subscribers: List[Callable[[EventMessage], Any]] = []
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def subscribe_to_events(self, callback: Callable[[EventMessage], Any]) -> None:
        self.subscribers.append(callback)

    async def _emit_event(self, event_type: ConnectionEvent, device_name: str, data: Optional[Dict[str, Any]] = None):
        msg = EventMessage(event_type=event_type, device_name=device_name, data=data)
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(msg)
                else:
                    callback(msg)
            except Exception as e:
                logger.error("event_callback_error", error=str(e))

    async def connect_device(self, host: str, user: str, password: Optional[str] = None):
        if host in self.sessions and self.sessions[host].state == ConnectionState.CONNECTED:
            return self.sessions[host]

        if len(self.sessions) >= self.max_sessions:
            raise RuntimeError(f"Connection pool full (max {self.max_sessions})")

        session = DeviceSession(host, user, password)
        self.sessions[host] = session

        def report_progress(message: str):
            asyncio.create_task(self._emit_event(ConnectionEvent.PROGRESS, host, {"message": message}))

        backoff = 1
        for attempt in range(self.retry_limit):
            logger.info("attempting_connection", device=host, attempt=attempt+1)
            report_progress(f"Connection attempt {attempt + 1}/{self.retry_limit}")
            
            success = await session.connect(progress_callback=report_progress)
            if success:
                await self._emit_event(ConnectionEvent.CONNECTED, host)
                return session
            
            await self._emit_event(ConnectionEvent.ERROR, host, {"attempt": attempt + 1})
            if attempt < self.retry_limit - 1:
                report_progress(f"Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff

        session.state = ConnectionState.FAILED
        return session

    async def disconnect_device(self, host: str):
        """Gracefully disconnects a device and removes it from active sessions."""
        if host in self.sessions:
            session = self.sessions[host]
            logger.info("disconnecting_device", device=host)
            
            try:
                # Add timeout to avoid hanging if the device is unresponsive
                await asyncio.wait_for(session.close(), timeout=5.0)
            except Exception as e:
                logger.error("disconnect_error", error=str(e), device=host)
            finally:
                session.state = ConnectionState.DISCONNECTED
                await self._emit_event(ConnectionEvent.DISCONNECTED, host)

    async def start_heartbeat(self, interval: int = 30):
        if self._heartbeat_task:
            return
        self._heartbeat_task = asyncio.create_task(self._run_heartbeat(interval))

    async def _run_heartbeat(self, interval: int):
        while True:
            await asyncio.sleep(interval)
            for host, session in list(self.sessions.items()):
                if session.state == ConnectionState.CONNECTED:
                    alive = await session.is_alive()
                    if not alive:
                        logger.warn("heartbeat_failed", device=host)
                        session.state = ConnectionState.DISCONNECTED
                        await self._emit_event(ConnectionEvent.DISCONNECTED, host)
                        # Try to reconnect? Or just let discovery engine handle it
                elif session.state == ConnectionState.DISCONNECTED:
                     # Maybe try to resume if it was intentional or transient
                     pass

    async def close_all(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_all()
