import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.config.models import (
    PulseConfig as PulseConfigModel,
    WebSocketConfig,
    APIConfig,
    EventConfig,
    RESTAPIConfig
)


class HealthWeights(BaseModel):
    optical: float = 0.4
    errors: float = 0.3
    stability: float = 0.3


class Thresholds(BaseModel):
    optical_power: Dict[str, float]
    error_ratio: Dict[str, float]
    alert_cooldown: int = 300
    health_weights: Optional[HealthWeights] = None
    trend_window_size: int = 5
    trend_sensitivity: float = 10.0


class PulseConfig(BaseModel):
    polling_interval: int
    connection_timeout: int
    retry_attempts: int
    cache_ttl: int
    thresholds: Thresholds
    sites: Dict[str, list[str]]
    ui: Dict[str, Any]

    # New config objects
    api: APIConfig
    websocket: WebSocketConfig
    events: EventConfig
    rest_api: RESTAPIConfig

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
            ),
            thresholds=Thresholds(**thresholds_data),
            sites=config_dict.get("sites", {}),
            ui=config_dict.get("ui", {})
        )


def load_config(config_path: str = "config.yaml") -> PulseConfig:
    """Load configuration from YAML file and return validated PulseConfig object."""
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    # Use the new from_dict method
    return PulseConfig.from_dict(data)
