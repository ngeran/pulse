"""
twamp_engine.py
───────────────
TWAMP (Two-Way Active Measurement Protocol) Data Engine

Fetches and parses TWAMP probe results from Juniper devices.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from structlog import get_logger
logger = get_logger()


class TWAMPMetrics:
    """Represents TWAMP probe metrics."""

    def __init__(
        self,
        owner: str,
        test_name: str,
        reflector_address: str,
        sender_address: str,
        avg_latency_usec: float,
        jitter_usec: float,
        loss_percentage: float,
        min_latency_usec: float,
        max_latency_usec: float,
        probes_sent: int,
        probes_received: int,
        status: str = "OK"
    ):
        self.owner = owner
        self.test_name = test_name
        self.reflector_address = reflector_address
        self.sender_address = sender_address
        self.avg_latency_usec = avg_latency_usec
        self.jitter_usec = jitter_usec
        self.loss_percentage = loss_percentage
        self.min_latency_usec = min_latency_usec
        self.max_latency_usec = max_latency_usec
        self.probes_sent = probes_sent
        self.probes_received = probes_received
        self.status = status
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "owner": self.owner,
            "test_name": self.test_name,
            "target": self.reflector_address,
            "latency": self.avg_latency_usec / 1000.0,  # Convert to ms
            "jitter": self.jitter_usec / 1000.0,  # Convert to ms
            "loss": self.loss_percentage,
            "status": self.status,
            "min_latency_ms": self.min_latency_usec / 1000.0,
            "max_latency_ms": self.max_latency_usec / 1000.0,
            "probes_sent": self.probes_sent,
            "probes_received": self.probes_received,
            "timestamp": self.timestamp.isoformat()
        }


class TWAMPEngine:
    """Engine for fetching TWAMP probe data from Juniper devices."""

    # Thresholds for status determination
    WARN_LATENCY_MS = 50.0
    CRIT_LATENCY_MS = 100.0
    WARN_JITTER_MS = 10.0
    CRIT_JITTER_MS = 30.0
    WARN_LOSS_PCT = 0.5
    CRIT_LOSS_PCT = 1.0

    def __init__(self):
        self.logger = logger

    def _determine_status(
        self,
        latency_ms: float,
        jitter_ms: float,
        loss_pct: float
    ) -> str:
        """Determine health status based on thresholds."""
        if (
            latency_ms >= self.CRIT_LATENCY_MS or
            jitter_ms >= self.CRIT_JITTER_MS or
            loss_pct >= self.CRIT_LOSS_PCT
        ):
            return "CRIT"
        elif (
            latency_ms >= self.WARN_LATENCY_MS or
            jitter_ms >= self.WARN_JITTER_MS or
            loss_pct >= self.WARN_LOSS_PCT
        ):
            return "WARN"
        return "OK"

    def parse_probe_results(self, rpc_reply: Any) -> List[TWAMPMetrics]:
        """
        Parse TWAMP probe results from RPC reply.

        Args:
            rpc_reply: PyEZ RPC reply from 'show services rpm twamp client probe-results'

        Returns:
            List of TWAMPMetrics objects
        """
        metrics_list = []

        try:
            # Convert RPC reply to string and parse JSON
            reply_str = str(rpc_reply)
            data = json.loads(reply_str)

            # Navigate through the JSON structure
            probe_results = data.get("probe-results", [])
            for probe_result in probe_results:
                test_results_list = probe_result.get("probe-test-results", [])

                for test_results in test_results_list:
                    # Extract basic test info
                    owner = self._extract_data(test_results.get("owner", [{}]))
                    test_name = self._extract_data(test_results.get("test-name", [{}]))
                    reflector_addr = self._extract_data(test_results.get("reflector-address", [{}]))
                    sender_addr = self._extract_data(test_results.get("sender-address", [{}]))

                    # Use global results for overall statistics
                    global_results = test_results.get("probe-test-global-results", [])
                    if not global_results:
                        continue

                    generic_results = global_results[0].get("probe-test-generic-results", [])
                    if not generic_results:
                        continue

                    results = generic_results[0]

                    # Extract RTT metrics
                    rtt_results = results.get("probe-test-rtt", [{}])[0].get("probe-summary-results", [{}])[0]
                    avg_latency = float(self._extract_data(rtt_results.get("avg-delay", [{"data": "0"}])))
                    min_latency = float(self._extract_data(rtt_results.get("min-delay", [{"data": "0"}])))
                    max_latency = float(self._extract_data(rtt_results.get("max-delay", [{"data": "0"}])))
                    jitter = float(self._extract_data(rtt_results.get("jitter-delay", [{"data": "0"}])))

                    # Extract loss percentage
                    loss_pct = float(results.get("loss-percentage", [{"data": "0.0"}])[0].get("data", "0.0"))

                    # Extract probe counts
                    probes_sent = int(results.get("probes-sent", [{"data": "0"}])[0].get("data", "0"))
                    probes_received = int(results.get("probe-responses", [{"data": "0"}])[0].get("data", "0"))

                    # Convert to ms and determine status
                    latency_ms = avg_latency / 1000.0
                    jitter_ms = jitter / 1000.0
                    status = self._determine_status(latency_ms, jitter_ms, loss_pct)

                    metrics = TWAMPMetrics(
                        owner=owner,
                        test_name=test_name,
                        reflector_address=reflector_addr,
                        sender_address=sender_addr,
                        avg_latency_usec=avg_latency,
                        jitter_usec=jitter,
                        loss_percentage=loss_pct,
                        min_latency_usec=min_latency,
                        max_latency_usec=max_latency,
                        probes_sent=probes_sent,
                        probes_received=probes_received,
                        status=status
                    )

                    metrics_list.append(metrics)
                    self.logger.debug(
                        "Parsed TWAMP metrics",
                        owner=owner,
                        test=test_name,
                        latency_ms=latency_ms,
                        jitter_ms=jitter_ms,
                        loss_pct=loss_pct,
                        status=status
                    )

        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            self.logger.error("Failed to parse TWAMP probe results", error=str(e))
        except Exception as e:
            self.logger.error("Unexpected error parsing TWAMP results", error=str(e))

        return metrics_list

    def _extract_data(self, field: List[Dict[str, Any]]) -> str:
        """Extract data field from Juniper JSON response structure."""
        if isinstance(field, list) and len(field) > 0:
            return field[0].get("data", "0")
        return "0"

    async def fetch_twamp_data(self, device_session) -> List[TWAMPMetrics]:
        """
        Fetch TWAMP probe data from a device.

        Args:
            device_session: Active DeviceSession with PyEZ connection

        Returns:
            List of TWAMPMetrics objects
        """
        metrics_list = []

        try:
            # Get PyEZ device
            dev = device_session.dev
            print(f"[DEBUG TWAMP] Fetching from device: {device_session.device_name}")

            # Execute RPC command for TWAMP probe results
            print(f"[DEBUG TWAMP] Executing RPC...")
            rpc_reply = dev.rpc.get_rpc(
                filter_xml="""<get-services-rpm-twamp-client-probe-results-information/>""",
                normalize=True
            )
            print(f"[DEBUG TWAMP] RPC reply received: {type(rpc_reply)}")

            # Parse the results
            print(f"[DEBUG TWAMP] Parsing results...")
            metrics_list = self.parse_probe_results(rpc_reply)
            print(f"[DEBUG TWAMP] Parsed {len(metrics_list)} metrics")

            self.logger.info(
                "Fetched TWAMP data",
                device=device_session.device_name,
                probe_count=len(metrics_list)
            )

        except Exception as e:
            self.logger.error(
                "Failed to fetch TWAMP data",
                device=device_session.device_name,
                error=str(e)
            )
            print(f"[ERROR TWAMP] Failed to fetch from {device_session.device_name}: {e}")
            import traceback
            traceback.print_exc()

        return metrics_list

    async def fetch_all_twamp_data(self, connection_manager) -> Dict[str, List[TWAMPMetrics]]:
        """
        Fetch TWAMP data from all connected devices.

        Args:
            connection_manager: ConnectionManager instance

        Returns:
            Dictionary mapping device names to their TWAMP metrics
        """
        all_metrics = {}

        sessions = connection_manager.sessions
        for device_name, session in sessions.items():
            if hasattr(session, 'state') and session.state.value == "CONNECTED":
                try:
                    metrics = await self.fetch_twamp_data(session)
                    all_metrics[device_name] = metrics
                except Exception as e:
                    self.logger.error(
                        "Error fetching TWAMP from device",
                        device=device_name,
                        error=str(e)
                    )

        return all_metrics
