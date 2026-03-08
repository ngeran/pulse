"""
health_models.py
────────────────
Data models for circuit health monitoring.

Defines all dataclasses for optical diagnostics, interface errors,
health scoring, alerts, and monitoring configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, List, Optional, Any
import statistics


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class HealthSeverity(str, Enum):
    """Health alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TrendDirection(str, Enum):
    """Trend analysis results"""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DEGRADING = "DEGRADING"


# ──────────────────────────────────────────────────────────────────────────────
# Optical and Error Data
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OpticalDiagnostics:
    """Optical metrics from 'show interfaces diagnostics optics'"""
    # Current values
    laser_output_power: float        # dBm (tx power)
    rx_signal_power: float           # dBm (rx power)
    module_temperature: float        # Celsius
    laser_bias_current: float        # mA

    # Thresholds (from Junos)
    laser_output_high_alarm: Optional[float] = None
    laser_output_high_warning: Optional[float] = None
    laser_output_low_warning: Optional[float] = None
    laser_output_low_alarm: Optional[float] = None

    rx_signal_high_alarm: Optional[float] = None
    rx_signal_high_warning: Optional[float] = None
    rx_signal_low_warning: Optional[float] = None
    rx_signal_low_alarm: Optional[float] = None

    temp_high_alarm: Optional[float] = None
    temp_high_warning: Optional[float] = None
    temp_low_warning: Optional[float] = None
    temp_low_alarm: Optional[float] = None

    bias_high_alarm: Optional[float] = None
    bias_high_warning: Optional[float] = None
    bias_low_warning: Optional[float] = None
    bias_low_alarm: Optional[float] = None

    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "laser_output_power": self.laser_output_power,
            "rx_signal_power": self.rx_signal_power,
            "module_temperature": self.module_temperature,
            "laser_bias_current": self.laser_bias_current,
            "thresholds": {
                "laser_output": {
                    "high_alarm": self.laser_output_high_alarm,
                    "high_warning": self.laser_output_high_warning,
                    "low_warning": self.laser_output_low_warning,
                    "low_alarm": self.laser_output_low_alarm,
                },
                "rx_signal": {
                    "high_alarm": self.rx_signal_high_alarm,
                    "high_warning": self.rx_signal_high_warning,
                    "low_warning": self.rx_signal_low_warning,
                    "low_alarm": self.rx_signal_low_alarm,
                },
                "temperature": {
                    "high_alarm": self.temp_high_alarm,
                    "high_warning": self.temp_high_warning,
                    "low_warning": self.temp_low_warning,
                    "low_alarm": self.temp_low_alarm,
                },
                "bias_current": {
                    "high_alarm": self.bias_high_alarm,
                    "high_warning": self.bias_high_warning,
                    "low_warning": self.bias_low_warning,
                    "low_alarm": self.bias_low_alarm,
                },
            },
            "timestamp": self.timestamp,
        }


@dataclass
class InterfaceErrors:
    """Error counters from 'show interfaces extensive'"""
    input_errors: int
    output_errors: int
    input_crc_errors: int
    output_crc_errors: int
    input_drops: int
    output_drops: int
    carrier_transitions: int

    # Flap detection
    interface_flapped: Optional[str] = None  # timestamp
    flap_count: int = 0

    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_errors": self.input_errors,
            "output_errors": self.output_errors,
            "input_crc_errors": self.input_crc_errors,
            "output_crc_errors": self.output_crc_errors,
            "input_drops": self.input_drops,
            "output_drops": self.output_drops,
            "carrier_transitions": self.carrier_transitions,
            "interface_flapped": self.interface_flapped,
            "flap_count": self.flap_count,
            "timestamp": self.timestamp,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds and Configuration
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class HealthThresholds:
    """Configurable thresholds per interface"""
    # Optical thresholds (overrides device defaults if set)
    min_tx_power: Optional[float] = None      # dBm
    max_tx_power: Optional[float] = None
    min_rx_power: Optional[float] = None
    max_rx_power: Optional[float] = None
    min_rx_power_margin: Optional[float] = None  # dB above/below nominal

    # Error rate thresholds
    max_error_rate: Optional[float] = None    # errors/second
    max_crc_rate: Optional[float] = None       # CRC errors/second
    max_drop_rate: Optional[float] = None      # drops/second

    # Behavior thresholds
    max_carrier_transitions: Optional[int] = None
    max_flaps_per_hour: Optional[int] = None

    # Trend analysis sensitivity
    trend_window_size: int = 5                # Number of samples to analyze
    trend_sensitivity: float = 0.1            # 10% change triggers trend alert


# ──────────────────────────────────────────────────────────────────────────────
# Health Scoring
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class HealthScore:
    """Overall health assessment for an interface"""
    interface_name: str
    score: float                    # 0-100 (100 = healthy)
    severity: HealthSeverity
    primary_issue: str              # Human-readable description
    contributing_factors: List[str] = field(default_factory=list)

    # Individual metric scores
    optical_score: float = 100.0
    error_score: float = 100.0
    stability_score: float = 100.0

    # Trend data
    trend_direction: TrendDirection = TrendDirection.STABLE
    trend_description: str = ""

    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface_name": self.interface_name,
            "score": self.score,
            "severity": self.severity.value,
            "primary_issue": self.primary_issue,
            "contributing_factors": self.contributing_factors,
            "optical_score": self.optical_score,
            "error_score": self.error_score,
            "stability_score": self.stability_score,
            "trend_direction": self.trend_direction.value,
            "trend_description": self.trend_description,
            "timestamp": self.timestamp,
        }

    def get_legacy_status(self) -> str:
        """Convert to legacy RED/YELLOW/GREEN status for backward compatibility"""
        if self.score >= 80:
            return "GREEN"
        elif self.score >= 60:
            return "YELLOW"
        else:
            return "RED"


# ──────────────────────────────────────────────────────────────────────────────
# Metric History for Trend Analysis
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MetricHistory:
    """Historical data for trend analysis"""
    interface_key: str  # host:interface_name
    metric_name: str    # e.g., "rx_power", "error_rate"
    values: List[float] = field(default_factory=list)
    timestamps: List[str] = field(default_factory=list)
    max_samples: int = 100  # Keep last 100 samples

    def add_sample(self, value: float, timestamp: str) -> None:
        self.values.append(value)
        self.timestamps.append(timestamp)
        if len(self.values) > self.max_samples:
            self.values.pop(0)
            self.timestamps.pop(0)

    def get_trend(self, window_size: int = 5, sensitivity: float = 10.0) -> tuple[TrendDirection, str]:
        """
        Analyze trend over window_size samples.

        Returns:
            (TrendDirection, description_string)
        """
        if len(self.values) < window_size:
            return TrendDirection.STABLE, "Insufficient data"

        recent = self.values[-window_size:]
        older = self.values[-(window_size*2):-window_size] if len(self.values) >= window_size*2 else self.values[:window_size]

        if not older:
            return TrendDirection.STABLE, "Building history..."

        # Calculate averages
        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)

        # Calculate percent change
        if older_avg != 0:
            percent_change = ((recent_avg - older_avg) / older_avg) * 100
        else:
            # No change from zero
            percent_change = 0.0

        # Determine trend based on sensitivity
        if abs(percent_change) < sensitivity:
            return TrendDirection.STABLE, f"Stable ({percent_change:+.1f}%)"

        # Determine direction (context-aware: for most metrics, lower is bad)
        # This will be adjusted by the scoring engine based on metric type
        direction = "degrading" if percent_change < 0 else "improving"

        return (
            TrendDirection.DEGRADING if percent_change < 0 else TrendDirection.IMPROVING,
            f"{direction.capitalize()} ({percent_change:+.1f}% over {window_size} samples)"
        )
