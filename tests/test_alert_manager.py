"""
Tests for HealthAlertManager
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.core.health_alert_manager import HealthAlertManager, HealthAlert
from backend.core.health_models import (
    HealthScore,
    HealthSeverity,
    OpticalDiagnostics,
    InterfaceErrors,
    TrendDirection
)


def test_alert_cooldown():
    """Test that alerts are suppressed during cooldown period."""
    manager = HealthAlertManager(cooldown_seconds=60)

    # Create a critical score
    score = HealthScore(
        interface_name="et-0/0/0",
        score=30.0,
        severity=HealthSeverity.CRITICAL,
        primary_issue="RX power critically low"
    )

    interface_key = "router1:et-0/0/0"

    # First alert should be sent
    assert manager.should_alert(interface_key, score) is True

    # Record the alert
    manager.record_alert(interface_key)

    # Second alert should be suppressed (cooldown)
    assert manager.should_alert(interface_key, score) is False


def test_alert_severity_escalation():
    """Test that severity escalation bypasses cooldown."""
    manager = HealthAlertManager(cooldown_seconds=300)

    # Create warning score
    warning_score = HealthScore(
        interface_name="et-0/0/0",
        score=50.0,
        severity=HealthSeverity.WARNING,
        primary_issue="Performance degraded"
    )

    # Create critical score
    critical_score = HealthScore(
        interface_name="et-0/0/0",
        score=20.0,
        severity=HealthSeverity.CRITICAL,
        primary_issue="Multiple issues detected"
    )

    interface_key = "router1:et-0/0/0"

    # First warning alert
    assert manager.should_alert(interface_key, warning_score) is True
    manager.record_alert(interface_key)

    # Escalation to critical should bypass cooldown
    assert manager.should_alert(interface_key, critical_score, previous_score=warning_score) is True


def test_alert_degradation_trend():
    """Test that degrading trend triggers alert."""
    manager = HealthAlertManager(cooldown_seconds=300)

    # Create score with degrading trend
    degrading_score = HealthScore(
        interface_name="et-0/0/0",
        score=75.0,
        severity=HealthSeverity.INFO,
        primary_issue="All systems normal",
        trend_direction=TrendDirection.DEGRADING,
        trend_description="Metrics degrading"
    )

    interface_key = "router1:et-0/0/0"

    # Degradation should trigger alert even for INFO severity
    assert manager.should_alert(interface_key, degrading_score) is True


def test_alert_cooldown_expiry():
    """Test that alerts are sent after cooldown expires."""
    manager = HealthAlertManager(cooldown_seconds=1)  # 1 second cooldown

    score = HealthScore(
        interface_name="et-0/0/0",
        score=30.0,
        severity=HealthSeverity.CRITICAL,
        primary_issue="RX power critically low"
    )

    interface_key = "router1:et-0/0/0"

    # First alert
    assert manager.should_alert(interface_key, score) is True
    manager.record_alert(interface_key)

    # Second alert should be suppressed
    assert manager.should_alert(interface_key, score) is False

    # Wait for cooldown to expire
    import time
    time.sleep(1.1)

    # Alert should be allowed again
    assert manager.should_alert(interface_key, score) is True


def test_alert_generation():
    """Test HealthAlert generation."""
    manager = HealthAlertManager(cooldown_seconds=300)

    optical = OpticalDiagnostics(
        laser_output_power=-2.0,
        rx_signal_power=-20.0,
        module_temperature=40.0,
        laser_bias_current=10.0
    )

    errors = InterfaceErrors(
        input_errors=100,
        output_errors=50,
        input_crc_errors=10,
        output_crc_errors=5,
        input_drops=0,
        output_drops=0,
        carrier_transitions=2
    )

    score = HealthScore(
        interface_name="et-0/0/0",
        score=25.0,
        severity=HealthSeverity.CRITICAL,
        primary_issue="RX power critically low: -20.00 dBm",
        optical_score=30.0,
        error_score=70.0,
        stability_score=90.0,
        trend_direction=TrendDirection.DEGRADING,
        trend_description="Metrics degrading"
    )

    alert = manager.generate_alert("router1", "et-0/0/0", score, optical, errors)

    # Verify alert properties
    assert alert.host == "router1"
    assert alert.interface == "et-0/0/0"
    assert alert.severity == HealthSeverity.CRITICAL
    assert "CRITICAL" in alert.message
    assert alert.metric_name == "optical_health"  # Lowest component score
    assert alert.current_value == 30.0  # optical_score
    assert alert.trend_direction == TrendDirection.DEGRADING
    assert alert.optical_data is not None
    assert alert.error_data is not None


def test_alert_to_dict():
    """Test HealthAlert serialization."""
    manager = HealthAlertManager(cooldown_seconds=300)

    optical = OpticalDiagnostics(
        laser_output_power=-2.0,
        rx_signal_power=-10.0,
        module_temperature=45.0,
        laser_bias_current=12.0
    )

    errors = None

    score = HealthScore(
        interface_name="et-0/0/0",
        score=85.0,
        severity=HealthSeverity.INFO,
        primary_issue="All systems normal"
    )

    alert = manager.generate_alert("router1", "et-0/0/0", score, optical, errors)

    # Convert to dict
    alert_dict = alert.to_dict()

    # Verify dict structure
    assert "alert_id" in alert_dict
    assert alert_dict["host"] == "router1"
    assert alert_dict["interface"] == "et-0/0/0"
    assert alert_dict["severity"] == "INFO"
    assert alert_dict["optical_data"] is not None
    assert alert_dict["error_data"] is None


def test_cooldown_configuration():
    """Test cooldown period configuration."""
    manager = HealthAlertManager(cooldown_seconds=120)

    assert manager.get_cooldown_seconds() == 120

    manager.set_cooldown_seconds(300)
    assert manager.get_cooldown_seconds() == 300

    # Test negative values are clamped to 0
    manager.set_cooldown_seconds(-10)
    assert manager.get_cooldown_seconds() == 0


def test_multiple_interfaces_independent():
    """Test that different interfaces have independent cooldowns."""
    manager = HealthAlertManager(cooldown_seconds=60)

    score = HealthScore(
        interface_name="et-0/0/0",
        score=30.0,
        severity=HealthSeverity.CRITICAL,
        primary_issue="Critical issue"
    )

    interface1 = "router1:et-0/0/0"
    interface2 = "router1:et-0/0/1"

    # Alert on interface1
    assert manager.should_alert(interface1, score) is True
    manager.record_alert(interface1)

    # interface2 should still be able to alert
    assert manager.should_alert(interface2, score) is True

    # interface1 should be suppressed
    assert manager.should_alert(interface1, score) is False
