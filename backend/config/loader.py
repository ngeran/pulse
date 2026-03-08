import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

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

def load_config(config_path: str = "config.yaml") -> PulseConfig:
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)["pulse"]
        return PulseConfig(**data)
