"""
Configuration Model
────────────────────
Pydantic model for Pulse configuration with validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any


class WebSocketConfig(BaseModel):
    """WebSocket configuration."""
    ping_interval: int = Field(default=10, ge=1, le=60, description="Ping interval in seconds")
    ping_timeout: int = Field(default=10, ge=1, le=60, description="Ping timeout in seconds")
    close_timeout: int = Field(default=1, ge=1, le=10, description="Close timeout in seconds")
    max_message_size: int = Field(default=1048576, ge=1024, description="Max message size in bytes")
    base_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="Base reconnection delay in seconds")
    max_delay: float = Field(default=30.0, ge=1.0, le=300.0, description="Max reconnection delay in seconds")
    jitter: float = Field(default=0.2, ge=0.0, le=1.0, description="Reconnection jitter factor (±)")


class APIConfig(BaseModel):
    """FastAPI server configuration."""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8001, ge=1024, le=65535, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload")
    log_level: str = Field(default="info", description="Log level")
    workers: int = Field(default=1, ge=1, le=4, description="Number of worker processes")


class EventConfig(BaseModel):
    """Event handling configuration."""
    callback_timeout: float = Field(default=5.0, ge=0.1, le=60.0, description="Callback timeout in seconds")
    buffer_size: int = Field(default=1000, ge=100, le=10000, description="Event buffer size")
    serialize_events: bool = Field(default=True, description="Serialize events to JSON")


class RESTAPIConfig(BaseModel):
    """REST API configuration."""
    enabled: bool = Field(default=True, description="Enable REST API")
    rate_limit: int = Field(default=100, ge=10, le=1000, description="Rate limit per minute")
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")


class ThresholdConfig(BaseModel):
    """Threshold configuration."""
    optical_power_warn: float = Field(default=-12, description="Optical power warning threshold (dBm)")
    optical_power_critical: float = Field(default=-17, description="Optical power critical threshold (dBm)")
    error_ratio_warn: float = Field(default=0.0005, ge=0.0, le=1.0, description="Error ratio warning threshold")
    error_ratio_critical: float = Field(default=0.001, ge=0.0, le=1.0, description="Error ratio critical threshold")


class PulseConfig(BaseModel):
    """Main Pulse configuration."""
    polling_interval: int = Field(default=60, ge=10, le=3600)
    connection_timeout: int = Field(default=30, ge=5, le=300)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    cache_ttl: int = Field(default=300, ge=60, le=3600)

    api: APIConfig = Field(default_factory=APIConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    events: EventConfig = Field(default_factory=EventConfig)
    rest_api: RESTAPIConfig = Field(default_factory=RESTAPIConfig)

    # Flatten nested config for easier access
    @property
    def api_host(self) -> str:
        return self.api.host

    @property
    def api_port(self) -> int:
        return self.api.port

    @property
    def ws_ping_interval(self) -> int:
        return self.websocket.ping_interval

    @property
    def ws_ping_timeout(self) -> int:
        return self.websocket.ping_timeout

    @property
    def ws_close_timeout(self) -> int:
        return self.websocket.close_timeout

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PulseConfig":
        """Create config from dictionary (loaded from YAML)."""
        # Extract pulse config if nested
        if "pulse" in config_dict:
            config_dict = config_dict["pulse"]

        # Convert nested configs
        api_data = config_dict.get("api", {})
        ws_data = config_dict.get("websocket", {})
        events_data = config_dict.get("events", {})
        rest_data = config_dict.get("rest_api", {})
        thresholds_data = config_dict.get("thresholds", {})

        return cls(
            polling_interval=config_dict.get("polling_interval", 60),
            connection_timeout=config_dict.get("connection_timeout", 30),
            retry_attempts=config_dict.get("retry_attempts", 3),
            cache_ttl=config_dict.get("cache_ttl", 300),
            api=APIConfig(**api_data) if api_data else APIConfig(),
            websocket=WebSocketConfig(
                ping_interval=ws_data.get("ping_interval", 10),
                ping_timeout=ws_data.get("ping_timeout", 10),
                close_timeout=ws_data.get("close_timeout", 1),
                max_message_size=ws_data.get("max_message_size", 1048576),
                base_delay=ws_data.get("reconnect", {}).get("base_delay", 1.0),
                max_delay=ws_data.get("reconnect", {}).get("max_delay", 30.0),
                jitter=ws_data.get("reconnect", {}).get("jitter", 0.2)
            ),
            events=EventConfig(
                callback_timeout=events_data.get("callback_timeout", 5.0),
                buffer_size=events_data.get("buffer_size", 1000),
                serialize_events=events_data.get("serialize_events", True)
            ),
            rest_api=RESTAPIConfig(
                enabled=rest_data.get("enabled", True),
                rate_limit=rest_data.get("rate_limit", 100),
                timeout=rest_data.get("timeout", 30)
            )
        )
