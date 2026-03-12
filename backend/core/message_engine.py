"""
message_engine.py
────────────────
Central message bus for event routing, transformation, and broadcasting.

This module provides a unified event system that:
- Serializes backend events to WebSocket messages
- Routes events to subscribers
- Supports event filtering and aggregation
- Provides a single source of truth for event distribution
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

from backend.core.events import (
    EventMessage,
    ConnectionEvent,
    HealthEvent,
    BGPEvent,
    ARPEvent,
)
from backend.core.connection_engine import ConnectionManager
from backend.core.logic_engine import HealthScoringEngine
from backend.api.server import ConnectionManagerWS
from backend.utils.logging import logger


@dataclass
class EventBatch:
    """A batch of events to be processed together."""
    events: List[EventMessage]
    batch_id: str
    created_at: float
    source: str = "backend"


class MessageFilter:
    """
    Filter for routing events to specific subscribers.

    Attributes:
        event_types: Set of event types to include (None = all)
        devices: Set of device names to include (None = all)
        min_severity: Minimum severity level (INFO=0, SUCCESS=1, WARNING=2, ERROR=3)
    """

    SEVERITY_MAP = {
        "info": 0,
        "success": 1,
        "warning": 2,
        "error": 3,
    }

    def __init__(
        self,
        event_types: Optional[Set[Enum]] = None,
        devices: Optional[Set[str]] = None,
        min_severity: str = "info"
    ):
        self.event_types = event_types
        self.devices = devices
        self.min_severity = self.SEVERITY_MAP.get(min_severity.lower(), 0)

    def matches(self, event: EventMessage) -> bool:
        """Check if an event matches this filter."""
        # Check event type filter
        if self.event_types is not None and event.event_type not in self.event_types:
            return False

        # Check device filter
        if self.devices is not None and event.device_name not in self.devices:
            return False

        # Check severity filter (based on event type)
        severity = 0  # Default to info
        if event.event_type in (ConnectionEvent.ERROR, ConnectionEvent.STATE_CHANGED):
            if event.data and event.data.get("state") == "FAILED":
                severity = 3
            else:
                severity = 2
        elif event.event_type == ConnectionEvent.CONNECTED:
            severity = 1
        elif event.event_type in (HealthEvent.CIRCUIT_DEAD, HealthEvent.SPOF_DETECTED):
            severity = 3
        elif event.event_type == HealthEvent.CIRCUIT_SICK:
            severity = 2

        if severity < self.min_severity:
            return False

        return True


class MessageEngine:
    """
    Central message bus for event routing, transformation, and broadcasting.

    Features:
    - Unified event-to-message serialization
    - Event routing with filtering support
    - WebSocket broadcasting to all clients
    - Event aggregation (batching rapid events)
    - Subscription management
    - Event replay capability (for testing/debugging)

    Usage:
        engine = MessageEngine(conn_mgr, health_engine)
        await engine.start()

        # Events are now automatically routed:
        # Backend -> MessageEngine -> WebSocket Clients
    """

    def __init__(
        self,
        conn_mgr: ConnectionManager,
        health_engine: HealthScoringEngine,
        ws_port: int = 8001,
        enable_aggregation: bool = True,
        aggregation_window: float = 1.0,
        aggregation_size: int = 10,
    ):
        """
        Initialize the message engine.

        Args:
            conn_mgr: Connection manager for connection events
            health_engine: Health scoring engine for health events
            ws_port: WebSocket server port
            enable_aggregation: Enable event batching
            aggregation_window: Time window for batching (seconds)
            aggregation_size: Max events per batch
        """
        self.conn_mgr = conn_mgr
        self.health_engine = health_engine
        self.ws_port = ws_port

        # WebSocket manager
        self.ws_manager = ConnectionManagerWS()

        # Event serializers
        self.serializers: Dict[Enum, Callable] = {}
        self._register_default_serializers()

        # Subscription management
        self._filters: Dict[str, MessageFilter] = {}  # subscription_id -> filter
        self._subscriptions: Dict[str, Callable[[EventMessage], Any]] = {}
        self._lock = asyncio.Lock()

        # Event aggregation
        self.enable_aggregation = enable_aggregation
        self.aggregation_window = aggregation_window
        self.aggregation_size = aggregation_size
        self._pending_events: List[EventMessage] = []
        self._aggregation_timer: Optional[asyncio.TimerHandle] = None

        # Event history for replay
        self._event_history: List[EventMessage] = []
        self._max_history = 1000

        # State
        self._running = False
        self._backend_sub_ids: List[str] = []

    def _register_default_serializers(self):
        """Register default event serializers."""
        # Connection events
        self.register_serializer(ConnectionEvent.CONNECTED, self._serialize_connected)
        self.register_serializer(ConnectionEvent.DISCONNECTED, self._serialize_disconnected)
        self.register_serializer(ConnectionEvent.PROGRESS, self._serialize_progress)
        self.register_serializer(ConnectionEvent.ERROR, self._serialize_error)
        self.register_serializer(ConnectionEvent.STATE_CHANGED, self._serialize_state_changed)

        # Health events
        self.register_serializer(HealthEvent.CIRCUIT_SICK, self._serialize_circuit_sick)
        self.register_serializer(HealthEvent.CIRCUIT_DEAD, self._serialize_circuit_dead)
        self.register_serializer(HealthEvent.SPOF_DETECTED, self._serialize_spof_detected)
        self.register_serializer(HealthEvent.HEALTH_CHANGED, self._serialize_health_changed)
        self.register_serializer(HealthEvent.HEALTH_ALERT, self._serialize_health_alert)
        self.register_serializer(HealthEvent.TREND_DETECTED, self._serialize_trend_detected)

    def register_serializer(self, event_type: Enum, serializer: Callable[[EventMessage], str]):
        """Register a serializer function for an event type."""
        self.serializers[event_type] = serializer
        logger.debug("serializer_registered", event_type=str(event_type))

    async def start(self):
        """Start the message engine."""
        if self._running:
            logger.warning("message_engine_already_running")
            return

        self._running = True
        logger.info("message_engine_starting")

        # Subscribe to backend event sources
        conn_sub_id = await self.conn_mgr.subscribe_to_events(self._handle_connection_event)
        health_sub_id = await self.health_engine.subscribe_to_events(self._handle_health_event)
        self._backend_sub_ids = [conn_sub_id, health_sub_id]

        logger.info("message_engine_subscribed_to_backend")

        # Start WebSocket server
        from backend.api.server import start_websocket_server
        await start_websocket_server(self.ws_manager, port=self.ws_port)
        logger.info("message_engine_websocket_started", port=self.ws_port)

    async def stop(self):
        """Stop the message engine."""
        if not self._running:
            return

        self._running = False

        # Unsubscribe from backend
        for sub_id in self._backend_sub_ids:
            await self.conn_mgr.unsubscribe_from_events(sub_id)
            await self.health_engine.unsubscribe_from_events(sub_id)

        # Cancel aggregation timer
        if self._aggregation_timer:
            self._aggregation_timer.cancel()

        logger.info("message_engine_stopped")

    async def subscribe(
        self,
        handler: Callable[[EventMessage], Any],
        filter_obj: Optional[MessageFilter] = None
    ) -> str:
        """
        Subscribe to events with optional filtering.

        Args:
            handler: Callable that receives EventMessage
            filter_obj: Optional filter for event types/devices

        Returns:
            Subscription ID for unsubscribing
        """
        async with self._lock:
            sub_id = str(uuid.uuid4())
            self._subscriptions[sub_id] = handler
            if filter_obj:
                self._filters[sub_id] = filter_obj
            return sub_id

    async def unsubscribe(self, sub_id: str) -> bool:
        """
        Unsubscribe from events.

        Args:
            sub_id: Subscription ID from subscribe()

        Returns:
            True if subscription was removed
        """
        async with self._lock:
            return self._subscriptions.pop(sub_id, None) is not None

    async def _handle_connection_event(self, event: EventMessage):
        """Handle connection event from ConnectionManager."""
        await self._route_event(event)

    async def _handle_health_event(self, event: EventMessage):
        """Handle health event from HealthScoringEngine."""
        await self._route_event(event)

    async def _route_event(self, event: EventMessage):
        """
        Route an event through the message engine.

        This handles:
        - Event history tracking
        - Aggregation (if enabled)
        - Subscriber notifications
        - WebSocket broadcasting
        """
        # Add to history
        self._add_to_history(event)

        # Aggregate or broadcast immediately
        if self.enable_aggregation and self._should_aggregate(event):
            await self._add_to_aggregation(event)
        else:
            await self._broadcast_event(event)

    def _should_aggregate(self, event: EventMessage) -> bool:
        """Determine if an event should be aggregated."""
        # Aggregate PROGRESS and ERROR events
        if event.event_type in (ConnectionEvent.PROGRESS, ConnectionEvent.ERROR):
            return True

        # Don't aggregate CONNECTED, DISCONNECTED, STATE_CHANGED
        return False

    async def _add_to_aggregation(self, event: EventMessage):
        """Add event to aggregation batch."""
        self._pending_events.append(event)

        # Flush if we hit the batch size
        if len(self._pending_events) >= self.aggregation_size:
            await self._flush_aggregation()
        # Start timer if not running
        elif self._aggregation_timer is None:
            self._aggregation_timer = asyncio.get_event_loop().call_later(
                self.aggregation_window,
                self._flush_aggregation_sync
            )

    async def _flush_aggregation(self):
        """Flush pending events as a batch."""
        if not self._pending_events:
            return

        # Create batch
        batch = EventBatch(
            events=self._pending_events.copy(),
            batch_id=str(uuid.uuid4()),
            created_at=time.time()
        )
        self._pending_events = []
        self._aggregation_timer = None

        # Broadcast batch
        await self._broadcast_batch(batch)

    def _flush_aggregation_sync(self):
        """Synchronous wrapper for flushing aggregation (for timer callback)."""
        asyncio.create_task(self._flush_aggregation())

    async def _broadcast_event(self, event: EventMessage):
        """Broadcast a single event to all WebSocket clients."""
        # Serialize event
        message = self._serialize_event(event)

        # Broadcast to WebSocket clients
        await self.ws_manager.broadcast(message)

        # Notify local subscribers
        await self._notify_subscribers(event)

    async def _broadcast_batch(self, batch: EventBatch):
        """Broadcast a batch of events."""
        # Serialize batch
        message = self._serialize_batch(batch)

        # Broadcast to WebSocket clients
        await self.ws_manager.broadcast(message)

        # Notify local subscribers
        for event in batch.events:
            await self._notify_subscribers(event)

    async def _notify_subscribers(self, event: EventMessage):
        """Notify local subscribers about an event."""
        for sub_id, handler in self._subscriptions.items():
            try:
                # Apply filter if present
                if sub_id in self._filters:
                    if not self._filters[sub_id].matches(event):
                        continue

                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error("subscriber_error", sub_id=sub_id, error=str(e))

    def _serialize_event(self, event: EventMessage) -> str:
        """Serialize EventMessage to WebSocket JSON message."""
        serializer = self.serializers.get(event.event_type)
        if serializer:
            try:
                return serializer(event)
            except Exception as e:
                logger.error("serializer_error", event_type=str(event.event_type), error=str(e))

        # Fallback to default serialization
        return self._default_serialize(event)

    def _serialize_batch(self, batch: EventBatch) -> str:
        """Serialize an EventBatch to WebSocket JSON message."""
        return json.dumps({
            "type": "batch",
            "batch_id": batch.batch_id,
            "source": batch.source,
            "count": len(batch.events),
            "events": [self._event_to_dict(e) for e in batch.events]
        })

    def _event_to_dict(self, event: EventMessage) -> Dict[str, Any]:
        """Convert EventMessage to dictionary for JSON serialization."""
        return {
            "event_type": event.event_type.value,
            "device": event.device_name,
            "data": event.data,
            "timestamp": getattr(event, 'timestamp', time.time())
        }

    def _default_serialize(self, event: EventMessage) -> str:
        """Default serialization for events without specific serializer."""
        return self._event_to_dict(event).__class__.__name__

    def _add_to_history(self, event: EventMessage):
        """Add event to history (capped at max_history)."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_history(self, limit: Optional[int] = None) -> List[EventMessage]:
        """Get event history (optionally limited)."""
        if limit:
            return self._event_history[-limit:]
        return self._event_history.copy()

    # ===== Serializer Methods =====

    def _serialize_connected(self, event: EventMessage) -> str:
        """Serialize CONNECTED event."""
        return json.dumps({
            "type": "connected",
            "source": "connection",
            "device": event.device_name,
            "message": event.data.get("message", "") if event.data else "",
            "timestamp": time.time()
        })

    def _serialize_disconnected(self, event: EventMessage) -> str:
        """Serialize DISCONNECTED event."""
        return json.dumps({
            "type": "disconnected",
            "source": "connection",
            "device": event.device_name,
            "timestamp": time.time()
        })

    def _serialize_progress(self, event: EventMessage) -> str:
        """Serialize PROGRESS event."""
        return json.dumps({
            "type": "progress",
            "source": "connection",
            "device": event.device_name,
            "message": event.data.get("message", "") if event.data else "",
            "timestamp": time.time()
        })

    def _serialize_error(self, event: EventMessage) -> str:
        """Serialize ERROR event."""
        return json.dumps({
            "type": "error",
            "source": "connection",
            "device": event.device_name,
            "message": event.data.get("message", "") if event.data else "",
            "attempt": event.data.get("attempt") if event.data else None,
            "timestamp": time.time()
        })

    def _serialize_state_changed(self, event: EventMessage) -> str:
        """Serialize STATE_CHANGED event."""
        return json.dumps({
            "type": "state_changed",
            "source": "connection",
            "device": event.device_name,
            "state": event.data.get("state", "") if event.data else "",
            "timestamp": time.time()
        })

    def _serialize_circuit_sick(self, event: EventMessage) -> str:
        """Serialize CIRCUIT_SICK event."""
        return json.dumps({
            "type": "circuit_sick",
            "source": "health",
            "device": event.device_name,
            "timestamp": time.time()
        })

    def _serialize_circuit_dead(self, event: EventMessage) -> str:
        """Serialize CIRCUIT_DEAD event."""
        return json.dumps({
            "type": "circuit_dead",
            "source": "health",
            "device": event.device_name,
            "timestamp": time.time()
        })

    def _serialize_spof_detected(self, event: EventMessage) -> str:
        """Serialize SPOF_DETECTED event."""
        return json.dumps({
            "type": "spof_detected",
            "source": "health",
            "device": event.device_name,
            "timestamp": time.time()
        })

    def _serialize_health_changed(self, event: EventMessage) -> str:
        """Serialize HEALTH_CHANGED event."""
        return json.dumps({
            "type": "health_changed",
            "source": "health",
            "device": event.device_name,
            "data": event.data,
            "timestamp": time.time()
        })

    def _serialize_health_alert(self, event: EventMessage) -> str:
        """Serialize HEALTH_ALERT event."""
        return json.dumps({
            "type": "health_alert",
            "source": "health",
            "device": event.device_name,
            "data": event.data,
            "timestamp": time.time()
        })

    def _serialize_trend_detected(self, event: EventMessage) -> str:
        """Serialize TREND_DETECTED event."""
        return json.dumps({
            "type": "trend_detected",
            "source": "health",
            "device": event.device_name,
            "data": event.data,
            "timestamp": time.time()
        })
