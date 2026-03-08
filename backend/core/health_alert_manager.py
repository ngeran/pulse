"""
health_alert_manager.py
──────────────────────
Generates and suppresses alerts to avoid alert fatigue.

Features:
- Cooldown periods to prevent alert spam
- Severity escalation detection (INFO → WARNING → CRITICAL)
- Smart alert generation with context
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.core.health_models import (
    HealthScore,
    HealthSeverity,
    InterfaceErrors,
    OpticalDiagnostics,
    TrendDirection,
)


class HealthAlert:
    """Alert event for health issues."""

    def __init__(
        self,
        host: str,
        interface: str,
        alert_id: str,
        severity: HealthSeverity,
        message: str,
        metric_name: str,
        current_value: float,
        threshold_value: Optional[float] = None,
        trend_direction: Optional[TrendDirection] = None,
        optical_data: Optional[OpticalDiagnostics] = None,
        error_data: Optional[InterfaceErrors] = None,
        timestamp: str = ""
    ):
        self.host = host
        self.interface = interface
        self.alert_id = alert_id
        self.severity = severity
        self.message = message
        self.metric_name = metric_name
        self.current_value = current_value
        self.threshold_value = threshold_value
        self.trend_direction = trend_direction
        self.optical_data = optical_data
        self.error_data = error_data
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "host": self.host,
            "interface": self.interface,
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "trend_direction": self.trend_direction.value if self.trend_direction else None,
            "optical_data": self.optical_data.to_dict() if self.optical_data else None,
            "error_data": self.error_data.to_dict() if self.error_data else None,
            "timestamp": self.timestamp,
        }


class HealthAlertManager:
    """Generates and suppresses alerts to avoid alert fatigue."""

    def __init__(self, cooldown_seconds: int = 300):
        """
        Initialize the alert manager.

        Args:
            cooldown_seconds: Minimum seconds between alerts for the same interface (default: 5 minutes)
        """
        self._last_alert_time: Dict[str, str] = {}  # interface_key -> timestamp
        self._cooldown_seconds = cooldown_seconds
        self._alert_counter = 0

    def should_alert(
        self,
        interface_key: str,
        score: HealthScore,
        previous_score: Optional[HealthScore] = None
    ) -> bool:
        """
        Determine if an alert should be generated.

        Alert rules:
        1. Always alert on CRITICAL severity
        2. Alert on WARNING if not in cooldown
        3. Alert on severity escalation (INFO → WARNING → CRITICAL)
        4. Alert on trend degradation
        5. Suppress repeated INFO alerts

        Args:
            interface_key: Unique identifier for the interface (host:ifname)
            score: Current health score
            previous_score: Previous health score (for escalation detection)

        Returns:
            True if alert should be generated
        """
        now = datetime.now(timezone.utc)
        last_alert = self._last_alert_time.get(interface_key)

        # Check cooldown
        if last_alert:
            last_time = datetime.fromisoformat(last_alert)
            if (now - last_time).total_seconds() < self._cooldown_seconds:
                # Still in cooldown - only alert if severity escalated
                if previous_score and self._severity_escalated(previous_score, score):
                    return True
                return False

        # Alert on critical or warning
        if score.severity in (HealthSeverity.CRITICAL, HealthSeverity.WARNING):
            return True

        # Alert on trend degradation
        if score.trend_direction == TrendDirection.DEGRADING:
            return True

        return False

    def _severity_escalated(
        self,
        previous: HealthScore,
        current: HealthScore
    ) -> bool:
        """Check if severity increased."""
        order = [HealthSeverity.INFO, HealthSeverity.WARNING, HealthSeverity.CRITICAL]
        try:
            return order.index(current.severity) > order.index(previous.severity)
        except ValueError:
            return False

    def record_alert(self, interface_key: str) -> None:
        """Record that an alert was sent."""
        self._last_alert_time[interface_key] = datetime.now(timezone.utc).isoformat()

    def generate_alert(
        self,
        host: str,
        interface: str,
        score: HealthScore,
        optical: Optional[OpticalDiagnostics],
        errors: Optional[InterfaceErrors]
    ) -> HealthAlert:
        """
        Generate a HealthAlert object.

        Determines the primary metric causing the alert and includes
        relevant context (optical data, error data).
        """
        # Determine primary metric based on lowest component score
        metric_name = "overall"
        current_val = score.score
        threshold_val = 80.0  # Default threshold

        if score.optical_score < score.error_score and score.optical_score < score.stability_score:
            metric_name = "optical_health"
            current_val = score.optical_score
            threshold_val = 70.0
        elif score.error_score < score.stability_score:
            metric_name = "error_rate"
            current_val = score.error_score
            threshold_val = 70.0
        else:
            metric_name = "stability"
            current_val = score.stability_score
            threshold_val = 70.0

        return HealthAlert(
            host=host,
            interface=interface,
            alert_id=str(uuid.uuid4()),
            severity=score.severity,
            message=f"[{score.severity.value}] {interface}: {score.primary_issue}",
            metric_name=metric_name,
            current_value=current_val,
            threshold_value=threshold_val,
            trend_direction=score.trend_direction,
            optical_data=optical,
            error_data=errors,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def get_cooldown_seconds(self) -> int:
        """Get the current cooldown period."""
        return self._cooldown_seconds

    def set_cooldown_seconds(self, seconds: int) -> None:
        """
        Set the cooldown period.

        Args:
            seconds: Minimum seconds between alerts for the same interface
        """
        self._cooldown_seconds = max(0, seconds)
