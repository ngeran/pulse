from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time

class ConnectionEvent(Enum):
    CONNECTED = "device_connected"
    DISCONNECTED = "device_disconnected"
    ERROR = "connection_error"
    STATE_CHANGED = "connection_state_changed"
    PROGRESS = "connection_progress"

class HealthEvent(Enum):
    CIRCUIT_SICK = "circuit_degraded"
    CIRCUIT_DEAD = "circuit_failed"
    SPOF_DETECTED = "spof_warning"
    HEALTH_CHANGED = "health_score_updated"
    HEALTH_ALERT = "health_alert"
    TREND_DETECTED = "trend_detected"

class BGPEvent(Enum):
    NEIGHBOR_UP = "bgp_neighbor_up"
    NEIGHBOR_DOWN = "bgp_neighbor_down"
    NEIGHBOR_STATE_CHANGED = "bgp_neighbor_state_changed"

class ARPEvent(Enum):
    ENTRY_ADDED = "arp_entry_added"
    ENTRY_REMOVED = "arp_entry_removed"
    TABLE_CHANGED = "arp_table_changed"

@dataclass
class EventMessage:
    event_type: Enum
    device_name: str
    data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    source: str = "backend"
