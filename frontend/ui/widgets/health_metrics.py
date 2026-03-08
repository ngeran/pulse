"""
health_metrics.py
─────────────────
Health-specific widgets for Pulse dashboard.

Displays health scores, optical diagnostics, and interface metrics
using Pulse-style widgets.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from frontend.ui.widgets.pulse_widgets import MetricBar, StatusBadge, CompactTable


class HealthMetricBar(MetricBar):
    """
    Health score metric bar with specialized color coding.

    For health scores, higher is better:
    - 80-100: Green (healthy)
    - 60-79: Yellow (degraded)
    - 0-59: Red (critical)
    """

    def __init__(
        self,
        label: str = "Health Score",
        value: float = 100,
        show_percentage: bool = True,
        compact: bool = True,
        **kwargs
    ) -> None:
        # For health scores, we invert the thresholds
        thresholds = {"warning": 60, "critical": 40}
        super().__init__(
            label=label,
            value=value,
            max_value=100,
            show_percentage=show_percentage,
            compact=compact,
            thresholds=thresholds,
            **kwargs
        )

    def update_from_score(self, score_data: Dict[str, Any]) -> None:
        """
        Update from health score data.

        Args:
            score_data: Dictionary with 'score', 'severity', 'trend_direction', etc.
        """
        score = score_data.get("score", 0)
        self.update_value(score)

        # Update styling based on severity
        severity = score_data.get("severity", "INFO")
        if severity == "CRITICAL":
            self._status = "critical"
        elif severity == "WARNING":
            self._status = "degraded"
        else:
            self._status = "healthy"


class StatusBadgeWithTrend(StatusBadge):
    """
    Status badge with trend arrow for health status.

    Displays:
    - Health status icon
    - Health score
    - Trend indicator (↗ ↘ →)
    """

    def __init__(
        self,
        score_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        # Initialize with default values
        status = "healthy"
        label = "100"
        trend = "stable"

        if score_data:
            label = str(int(score_data.get("score", 0)))
            severity = score_data.get("severity", "INFO")

            if severity == "CRITICAL":
                status = "failed"
            elif severity == "WARNING":
                status = "degraded"
            else:
                status = "healthy"

            trend_dir = score_data.get("trend_direction", "STABLE").lower()
            if trend_dir == "improving":
                trend = "improving"
            elif trend_dir == "degrading":
                trend = "degrading"
            else:
                trend = "stable"

        super().__init__(status=status, label=label, trend=trend, **kwargs)

    def update_from_score(self, score_data: Dict[str, Any]) -> None:
        """
        Update from health score data.

        Args:
            score_data: Dictionary with health score information
        """
        label = str(int(score_data.get("score", 0)))
        severity = score_data.get("severity", "INFO")

        if severity == "CRITICAL":
            status = "failed"
            blink = True
        elif severity == "WARNING":
            status = "degraded"
            blink = False
        else:
            status = "healthy"
            blink = False

        trend_dir = score_data.get("trend_direction", "STABLE").lower()
        if trend_dir == "improving":
            trend = "improving"
        elif trend_dir == "degrading":
            trend = "degrading"
        else:
            trend = "stable"

        self.update_status(status, trend)
        self._label = label
        self._blink = blink
        self.update(self.render())


class OpticalMetricsTable(CompactTable):
    """
    Table displaying optical diagnostics for interfaces.

    Shows:
    - Interface name
    - TX/RX power
    - Temperature
    - Bias current
    - Alarm status
    """

    COLUMNS = ["Interface", "TX (dBm)", "RX (dBm)", "Temp (°C)", "Bias (mA)", "Status"]

    def __init__(self, **kwargs) -> None:
        super().__init__(
            columns=self.COLUMNS,
            rows=[],
            **kwargs
        )

    def update_from_diagnostics(self, diagnostics: Dict[str, Dict[str, Any]]) -> None:
        """
        Update table with optical diagnostics data.

        Args:
            diagnostics: Dict mapping interface names to diagnostic data
        """
        rows = []

        for interface, data in diagnostics.items():
            tx_power = data.get("laser_output_power", 0)
            rx_power = data.get("rx_signal_power", 0)
            temp = data.get("module_temperature", 0)
            bias = data.get("laser_bias_current", 0)

            # Determine status based on thresholds
            rx_low_alarm = data.get("rx_signal_low_alarm")
            rx_low_warn = data.get("rx_signal_low_warning")
            tx_low_alarm = data.get("laser_output_low_alarm")
            tx_low_warn = data.get("laser_output_low_warning")
            temp_high_alarm = data.get("temp_high_alarm")
            temp_high_warn = data.get("temp_high_warning")

            status = "✓"
            if rx_low_alarm and rx_power <= rx_low_alarm:
                status = "⚠"
            elif tx_low_alarm and tx_power <= tx_low_alarm:
                status = "⚠"
            elif temp_high_alarm and temp >= temp_high_alarm:
                status = "⚠"

            row = [
                interface,
                f"{tx_power:.2f}",
                f"{rx_power:.2f}",
                f"{temp:.1f}",
                f"{bias:.1f}",
                status
            ]
            rows.append(row)

        self.set_rows(rows)


class ComponentScoresPanel(Static):
    """
    Panel displaying component health scores.

    Shows individual scores for:
    - Optical health (40%)
    - Error rate (30%)
    - Stability (30%)
    """

    DEFAULT_CSS = """
    ComponentScoresPanel {
        height: 100%;
        width: 100%;
    }

    .component-title {
        text-style: bold;
        color: $accent;
        margin: 0 1;
    }

    .component-row {
        margin: 0 1;
        height: 1;
    }
    """

    def __init__(self, title: str = "Component Scores", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._scores = {
            "optical": 100.0,
            "errors": 100.0,
            "stability": 100.0
        }

    def update_from_score(self, score_data: Dict[str, Any]) -> None:
        """
        Update from health score data.

        Args:
            score_data: Dictionary with component scores
        """
        self._scores = {
            "optical": score_data.get("optical_score", 100),
            "errors": score_data.get("error_score", 100),
            "stability": score_data.get("stability_score", 100)
        }
        self.update(self.render())

    def render(self) -> str:
        lines = [f"[component-title]{self._title}[/component_title]", ""]

        for component, score in self._scores.items():
            # Determine color and bar
            if score >= 80:
                color = "green"
                filled = int(score / 10)
            elif score >= 60:
                color = "yellow"
                filled = int(score / 10)
            else:
                color = "red"
                filled = int(score / 10)

            empty = 10 - filled
            bar = f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"

            label_map = {
                "optical": "Optical",
                "errors": "Errors",
                "stability": "Stability"
            }

            lines.append(
                f"[component-row]{label_map[component]}: {bar} {score:.0f}%[/component-row]"
            )

        return "\n".join(lines)


class TrendIndicator(Static):
    """
    Small widget showing trend direction with icon and description.

    Displays trend arrows and description from health score data.
    """

    DEFAULT_CSS = """
    TrendIndicator {
        height: 1;
    }

    .trend-icon {
        text-style: bold;
    }

    .trend-desc {
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._trend = "STABLE"
        self._description = "No trend data"

    def update_from_score(self, score_data: Dict[str, Any]) -> None:
        """
        Update from health score data.

        Args:
            score_data: Dictionary with trend information
        """
        self._trend = score_data.get("trend_direction", "STABLE")
        self._description = score_data.get("trend_description", "No trend data")
        self.update(self.render())

    def render(self) -> str:
        trend_map = {
            "IMPROVING": ("↗", "green"),
            "STABLE": ("→", "cyan"),
            "DEGRADING": ("↘", "yellow"),
            "CRITICAL": ("⚠", "red")
        }

        icon, color = trend_map.get(self._trend, ("→", "cyan"))

        return f"[trend-icon][{color}]{icon}[/{color}][/trend-icon] [trend-desc]{self._description}[/trend-desc]"
