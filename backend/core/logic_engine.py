import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from backend.core.events import HealthEvent, EventMessage
from backend.core.connection_engine import ConnectionManager
from backend.core.health_models import (
    HealthScore,
    HealthSeverity,
    HealthThresholds,
    InterfaceErrors,
    MetricHistory,
    OpticalDiagnostics,
    TrendDirection,
)
from backend.core.health_alert_manager import HealthAlertManager
from backend.utils.logging import logger
from jnpr.junos.factory.factory_loader import FactoryLoader
import yaml
import os

# Load PyEZ definitions
with open(os.path.join(os.path.dirname(__file__), "metrics_def.yaml"), "r") as f:
    _definitions = yaml.safe_load(f)
    globals().update(FactoryLoader().load(_definitions))


class HealthScoringEngine:
    def __init__(self, conn_manager: ConnectionManager, config: Any):
        self.conn_manager = conn_manager
        self.config = config
        self.subscribers: Dict[str, Callable[[EventMessage], Any]] = {}
        self.circuit_states: Dict[str, HealthScore] = {}  # host:interface -> HealthScore
        self.metric_history: Dict[str, Dict[str, MetricHistory]] = {}  # host -> {metric_name: MetricHistory}
        self._lock = asyncio.Lock()  # Lock for thread-safe operations

        # Load thresholds from config
        self.thresholds = self._load_thresholds()

        # Initialize alert manager
        cooldown_seconds = getattr(config.thresholds, 'alert_cooldown', 300)
        self.alert_manager = HealthAlertManager(cooldown_seconds=cooldown_seconds)

    def _load_thresholds(self) -> HealthThresholds:
        """Load health thresholds from configuration."""
        return HealthThresholds(
            min_rx_power=self.config.thresholds.optical_power.get("critical"),
            min_rx_power_margin=self.config.thresholds.optical_power.get("warn"),
        )

    async def subscribe_to_events(self, callback: Callable[[EventMessage], Any]) -> str:
        """
        Subscribe to health events.

        Args:
            callback: Async or sync callable that receives EventMessage

        Returns:
            Subscription ID that can be used to unsubscribe
        """
        async with self._lock:
            sub_id = str(uuid.uuid4())
            self.subscribers[sub_id] = callback
            return sub_id

    async def unsubscribe_from_events(self, sub_id: str) -> bool:
        """
        Unsubscribe from health events.

        Args:
            sub_id: Subscription ID returned from subscribe_to_events()

        Returns:
            True if subscription was removed, False if not found
        """
        async with self._lock:
            return self.subscribers.pop(sub_id, None) is not None

    async def _emit_event(self, event_type: HealthEvent, device_name: str, data: Optional[Dict[str, Any]] = None):
        msg = EventMessage(event_type=event_type, device_name=device_name, data=data)
        for callback in self.subscribers.values():
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(msg)
                else:
                    callback(msg)
            except Exception as e:
                logger.error("event_callback_error", error=str(e), device=device_name)
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(msg)
                else:
                    callback(msg)
            except Exception as e:
                logger.error("health_event_callback_error", error=str(e))

    def _get_or_create_history(self, host: str, interface: str, metric_name: str) -> MetricHistory:
        """Get or create metric history for trend analysis."""
        if host not in self.metric_history:
            self.metric_history[host] = {}

        interface_key = f"{host}:{interface}"
        full_metric_key = f"{interface_key}:{metric_name}"

        if full_metric_key not in self.metric_history[host]:
            self.metric_history[host][full_metric_key] = MetricHistory(
                interface_key=interface_key,
                metric_name=metric_name
            )

        return self.metric_history[host][full_metric_key]

    def _update_history(self, host: str, interface: str, optical: Optional[OpticalDiagnostics], errors: Optional[InterfaceErrors]):
        """Update metric history with new data."""
        timestamp = datetime.now(timezone.utc).isoformat()

        if optical:
            self._get_or_create_history(host, interface, "rx_power").add_sample(optical.rx_signal_power, timestamp)
            self._get_or_create_history(host, interface, "tx_power").add_sample(optical.laser_output_power, timestamp)
            self._get_or_create_history(host, interface, "temperature").add_sample(optical.module_temperature, timestamp)
            self._get_or_create_history(host, interface, "bias_current").add_sample(optical.laser_bias_current, timestamp)

        if errors:
            self._get_or_create_history(host, interface, "input_errors").add_sample(errors.input_errors, timestamp)
            self._get_or_create_history(host, interface, "output_errors").add_sample(errors.output_errors, timestamp)
            self._get_or_create_history(host, interface, "carrier_transitions").add_sample(errors.carrier_transitions, timestamp)

    def _get_interface_history(self, host: str, interface: str) -> Dict[str, MetricHistory]:
        """Get all history for an interface."""
        interface_key = f"{host}:{interface}"
        if host not in self.metric_history:
            return {}

        return {
            k: v for k, v in self.metric_history[host].items()
            if v.interface_key == interface_key
        }

    def calculate_score(
        self,
        optical: Optional[OpticalDiagnostics],
        errors: Optional[InterfaceErrors],
        thresholds: HealthThresholds,
        history: Dict[str, MetricHistory],
        interface_name: str = ""
    ) -> HealthScore:
        """
        Calculate overall health score (0-100).

        Scoring components:
        - Optical score (40%): Power levels within thresholds
        - Error score (30%): Error rates, CRC errors
        - Stability score (30%): Carrier transitions, flaps
        """
        score = HealthScore(
            interface_name=interface_name,
            score=100.0,
            severity=HealthSeverity.INFO,
            primary_issue="All systems normal",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Optical scoring (40% weight)
        score.optical_score = self._score_optical(optical, thresholds)

        # Error scoring (30% weight)
        score.error_score = self._score_errors(errors, thresholds)

        # Stability scoring (30% weight)
        score.stability_score = self._score_stability(errors, thresholds)

        # Weighted overall score
        score.score = (
            score.optical_score * 0.4 +
            score.error_score * 0.3 +
            score.stability_score * 0.3
        )

        # Determine severity and primary issue
        score.severity, score.primary_issue = self._determine_severity(
            score, optical, errors, thresholds
        )

        # Analyze trends
        score.trend_direction, score.trend_description = self._analyze_trends(
            history, thresholds
        )

        return score

    def _score_optical(
        self,
        optical: Optional[OpticalDiagnostics],
        thresholds: HealthThresholds
    ) -> float:
        """Score optical metrics (0-100). Lower power = lower score."""
        if not optical:
            return 100.0  # No data = assume healthy

        deductions = 0.0

        # TX power check
        if optical.laser_output_low_alarm and optical.laser_output_power <= optical.laser_output_low_alarm:
            deductions += 40
        elif optical.laser_output_low_warning and optical.laser_output_power <= optical.laser_output_low_warning:
            deductions += 20
        elif thresholds.min_tx_power and optical.laser_output_power < thresholds.min_tx_power:
            deductions += 30

        # RX power check (most critical)
        if optical.rx_signal_low_alarm and optical.rx_signal_power <= optical.rx_signal_low_alarm:
            deductions += 50
        elif optical.rx_signal_low_warning and optical.rx_signal_power <= optical.rx_signal_low_warning:
            deductions += 25
        elif thresholds.min_rx_power and optical.rx_signal_power < thresholds.min_rx_power:
            deductions += 35

        # Temperature check
        if optical.temp_high_alarm and optical.module_temperature >= optical.temp_high_alarm:
            deductions += 20
        elif optical.temp_high_warning and optical.module_temperature >= optical.temp_high_warning:
            deductions += 10

        # Bias current check
        if optical.bias_high_alarm and optical.laser_bias_current >= optical.bias_high_alarm:
            deductions += 15
        elif optical.bias_high_warning and optical.laser_bias_current >= optical.bias_high_warning:
            deductions += 8

        return max(0.0, 100.0 - deductions)

    def _score_errors(
        self,
        errors: Optional[InterfaceErrors],
        thresholds: HealthThresholds
    ) -> float:
        """Score error metrics (0-100). More errors = lower score."""
        if not errors:
            return 100.0

        deductions = 0.0

        # Check for non-zero errors
        if errors.input_errors > 0 or errors.output_errors > 0:
            error_count = errors.input_errors + errors.output_errors
            if error_count > 1000:
                deductions += 50
            elif error_count > 100:
                deductions += 30
            elif error_count > 10:
                deductions += 10

        # CRC errors are particularly bad
        if errors.input_crc_errors > 0 or errors.output_crc_errors > 0:
            crc_count = errors.input_crc_errors + errors.output_crc_errors
            if crc_count > 100:
                deductions += 40
            elif crc_count > 10:
                deductions += 20

        # Drops indicate congestion or issues
        if errors.input_drops > 0 or errors.output_drops > 0:
            drop_count = errors.input_drops + errors.output_drops
            if drop_count > 1000:
                deductions += 30
            elif drop_count > 100:
                deductions += 15

        return max(0.0, 100.0 - deductions)

    def _score_stability(
        self,
        errors: Optional[InterfaceErrors],
        thresholds: HealthThresholds
    ) -> float:
        """Score interface stability (0-100). Flapping = low score."""
        if not errors:
            return 100.0

        deductions = 0.0

        # Carrier transitions indicate physical issues
        if errors.carrier_transitions > 10:
            deductions += 60
        elif errors.carrier_transitions > 3:
            deductions += 30
        elif errors.carrier_transitions > 0:
            deductions += 10

        # Interface flaps
        if errors.flap_count > 5:
            deductions += 40

        return max(0.0, 100.0 - deductions)

    def _determine_severity(
        self,
        score: HealthScore,
        optical: Optional[OpticalDiagnostics],
        errors: Optional[InterfaceErrors],
        thresholds: HealthThresholds,
    ) -> tuple[HealthSeverity, str]:
        """Determine alert severity and primary issue."""

        # Check for critical threshold breaches first
        if optical:
            # RX power critical
            if optical.rx_signal_low_alarm and optical.rx_signal_power <= optical.rx_signal_low_alarm:
                return HealthSeverity.CRITICAL, f"RX power critically low: {optical.rx_signal_power:.2f} dBm"

            # TX power critical
            if optical.laser_output_low_alarm and optical.laser_output_power <= optical.laser_output_low_alarm:
                return HealthSeverity.CRITICAL, f"TX power critically low: {optical.laser_output_power:.2f} dBm"

            # Temperature critical
            if optical.temp_high_alarm and optical.module_temperature >= optical.temp_high_alarm:
                return HealthSeverity.CRITICAL, f"Module temperature critical: {optical.module_temperature:.1f}°C"

        # Check for high error rates
        if errors and (errors.input_errors > 1000 or errors.output_errors > 1000):
            return HealthSeverity.CRITICAL, f"High error count: {errors.input_errors + errors.output_errors} errors"

        # Check score-based severity
        if score.score < 40:
            return HealthSeverity.CRITICAL, f"Multiple issues detected (score: {score.score:.0f}/100)"
        elif score.score < 60:
            return HealthSeverity.WARNING, f"Performance degraded (score: {score.score:.0f}/100)"
        elif score.score < 80:
            return HealthSeverity.WARNING, f"Minor issues detected (score: {score.score:.0f}/100)"

        return HealthSeverity.INFO, score.primary_issue

    def _analyze_trends(
        self,
        history: Dict[str, MetricHistory],
        thresholds: HealthThresholds
    ) -> tuple[TrendDirection, str]:
        """Analyze trends across all metrics."""
        if not history:
            return TrendDirection.STABLE, "No trend data yet"

        # Analyze key metrics
        trends = []
        for metric_name, metric_history in history.items():
            if len(metric_history.values) >= thresholds.trend_window_size:
                direction, desc = metric_history.get_trend(thresholds.trend_window_size)
                trends.append((direction, metric_name, desc))

        if not trends:
            return TrendDirection.STABLE, "Collecting trend data..."

        # Find most concerning trend (context-aware)
        # For error metrics, INCREASING is bad
        # For optical metrics, DECREASING is bad
        for direction, metric_name, desc in trends:
            if metric_name in ("input_errors", "output_errors", "carrier_transitions"):
                if direction == TrendDirection.IMPROVING:  # Values decreasing = good
                    continue
                elif direction == TrendDirection.DEGRADING:  # Values increasing = bad
                    return TrendDirection.DEGRADING, f"Errors increasing: {desc}"

        # For optical metrics, check for degradation
        degrading_trends = [t for t in trends if t[0] == TrendDirection.DEGRADING]
        if degrading_trends:
            return TrendDirection.DEGRADING, f"Metrics degrading: {degrading_trends[0][2]}"

        return TrendDirection.STABLE, "All metrics stable"

    async def analyze_device(self, host: str, interfaces: List[str]) -> Dict[str, HealthScore]:
        """Analyze device interfaces and return health scores."""
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {iface: HealthScore(
                interface_name=iface,
                score=0.0,
                severity=HealthSeverity.INFO,
                primary_issue="Device not connected",
                timestamp=datetime.now(timezone.utc).isoformat()
            ) for iface in interfaces}

        try:
            loop = asyncio.get_event_loop()

            # Fetch optics and errors
            optics_table = OpticalTable(session.dev)
            errors_table = ErrorTable(session.dev)

            optics_data = await loop.run_in_executor(None, optics_table.get)
            errors_data = await loop.run_in_executor(None, errors_table.get)

            results = {}
            for iface in interfaces:
                # Find metrics for iface
                opt = next((o for o in optics_data if o.name == iface), None)
                err = next((e for e in errors_data if e.name == iface), None)

                # Build optical diagnostics
                optical = None
                if opt:
                    optical = OpticalDiagnostics(
                        laser_output_power=float(opt.laser_output_power) if opt.laser_output_power else 0.0,
                        rx_signal_power=float(opt.rx_power) if opt.rx_power else 0.0,
                        module_temperature=float(opt.module_temperature) if opt.module_temperature else 0.0,
                        laser_bias_current=float(opt.laser_bias_current) if opt.laser_bias_current else 0.0,
                        laser_output_low_alarm=float(opt.laser_output_low_alarm) if opt.laser_output_low_alarm else None,
                        laser_output_low_warning=float(opt.laser_output_low_warning) if opt.laser_output_low_warning else None,
                        rx_signal_low_alarm=float(opt.rx_signal_low_alarm) if opt.rx_signal_low_alarm else None,
                        rx_signal_low_warning=float(opt.rx_signal_low_warning) if opt.rx_signal_low_warning else None,
                        temp_high_alarm=float(opt.temp_high_alarm) if opt.temp_high_alarm else None,
                        temp_high_warning=float(opt.temp_high_warning) if opt.temp_high_warning else None,
                        bias_high_alarm=float(opt.bias_high_alarm) if opt.bias_high_alarm else None,
                        bias_high_warning=float(opt.bias_high_warning) if opt.bias_high_warning else None,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )

                # Build interface errors
                errors = None
                if err:
                    errors = InterfaceErrors(
                        input_errors=int(err.input_errors) if err.input_errors else 0,
                        output_errors=int(err.output_errors) if err.output_errors else 0,
                        input_crc_errors=int(err.input_crc_errors) if hasattr(err, 'input_crc_errors') and err.input_crc_errors else 0,
                        output_crc_errors=int(err.output_crc_errors) if hasattr(err, 'output_crc_errors') and err.output_crc_errors else 0,
                        input_drops=int(err.input_drops) if err.input_drops else 0,
                        output_drops=int(err.output_drops) if err.output_drops else 0,
                        carrier_transitions=int(err.carrier_transitions) if err.carrier_transitions else 0,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )

                # Update history
                self._update_history(host, iface, optical, errors)

                # Get history for this interface
                history = self._get_interface_history(host, iface)

                # Calculate score
                health_score = self.calculate_score(optical, errors, self.thresholds, history, iface)
                results[iface] = health_score

                # Event emission for state change
                key = f"{host}:{iface}"
                old_score = self.circuit_states.get(key)

                # Check if we should alert using the alert manager
                should_emit_alert = self.alert_manager.should_alert(key, health_score, old_score)

                if old_score and old_score.score != health_score.score:
                    await self._emit_event(
                        HealthEvent.HEALTH_CHANGED,
                        host,
                        {
                            "interface": iface,
                            "old_score": old_score.to_dict(),
                            "new_score": health_score.to_dict()
                        }
                    )

                self.circuit_states[key] = health_score

                # Emit trend events
                if health_score.trend_direction != TrendDirection.STABLE:
                    await self._emit_event(
                        HealthEvent.TREND_DETECTED,
                        host,
                        {
                            "interface": iface,
                            "trend": health_score.trend_direction.value,
                            "description": health_score.trend_description,
                            "score": health_score.to_dict()
                        }
                    )

                # Emit alerts based on severity and alert manager decision
                if should_emit_alert:
                    # Generate alert with context
                    alert = self.alert_manager.generate_alert(host, iface, health_score, optical, errors)
                    self.alert_manager.record_alert(key)

                    await self._emit_event(
                        HealthEvent.HEALTH_ALERT,
                        host,
                        {
                            "interface": iface,
                            "alert": alert.to_dict(),
                            "score": health_score.to_dict()
                        }
                    )

                # Emit circuit events for backward compatibility
                if health_score.severity == HealthSeverity.CRITICAL:
                    await self._emit_event(
                        HealthEvent.CIRCUIT_DEAD,
                        host,
                        {
                            "interface": iface,
                            "score": health_score.to_dict()
                        }
                    )
                elif health_score.severity == HealthSeverity.WARNING:
                    await self._emit_event(
                        HealthEvent.CIRCUIT_SICK,
                        host,
                        {
                            "interface": iface,
                            "score": health_score.to_dict()
                        }
                    )

            return results
        except Exception as e:
            logger.error("health_analysis_failed", device=host, error=str(e))
            return {iface: HealthScore(
                interface_name=iface,
                score=0.0,
                severity=HealthSeverity.INFO,
                primary_issue=f"Analysis failed: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat()
            ) for iface in interfaces}

    async def check_spof(self):
        """Check for single points of failure across sites."""
        # Site awareness from config
        for site, routers in self.config.sites.items():
            healthy_count = 0
            site_results = []

            for router in routers:
                # Get scores for this router
                router_health = [v.score for k, v in self.circuit_states.items() if k.startswith(f"{router}:")]
                if all(h >= 80 for h in router_health) and router_health:
                    healthy_count += 1

            if healthy_count <= 1:
                await self._emit_event(
                    HealthEvent.SPOF_DETECTED,
                    site,
                    {"healthy_routers": healthy_count}
                )
