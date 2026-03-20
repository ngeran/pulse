"""
device_manager.py
─────────────────
Enhanced device management with grouping, polling, and interface selection.
Extends ConnectionManager with device management specific features.
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from datetime import datetime, timedelta
from backend.core.connection_engine import ConnectionManager, DeviceSession, ConnectionState
from backend.core.events import ConnectionEvent, EventMessage, HealthEvent
from backend.core.twamp_engine import TWAMPEngine
from backend.utils.logging import logger


class PollingInterval(Enum):
    """Polling interval options."""
    MANUAL = 0
    ONE_MIN = 60
    THREE_MIN = 180
    FIVE_MIN = 300
    TEN_MIN = 600
    FIFTEEN_MIN = 900


class DeviceGroup:
    """Represents a group of devices (e.g., by location)."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.devices: Set[str] = set()  # Set of device hostnames
        self.monitored_interfaces: Dict[str, Set[str]] = {}  # device -> set of interfaces

    def add_device(self, host: str) -> None:
        """Add a device to this group."""
        self.devices.add(host)

    def remove_device(self, host: str) -> None:
        """Remove a device from this group."""
        self.devices.discard(host)
        if host in self.monitored_interfaces:
            del self.monitored_interfaces[host]

    def add_interface(self, host: str, interface: str) -> None:
        """Add an interface to monitor for a device."""
        if host not in self.monitored_interfaces:
            self.monitored_interfaces[host] = set()
        self.monitored_interfaces[host].add(interface)

    def remove_interface(self, host: str, interface: str) -> None:
        """Remove an interface from monitoring."""
        if host in self.monitored_interfaces:
            self.monitored_interfaces[host].discard(interface)

    def get_interfaces(self, host: str) -> Set[str]:
        """Get monitored interfaces for a device."""
        return self.monitored_interfaces.get(host, set())


class DeviceManager:
    """
    Enhanced device manager with grouping and polling capabilities.
    Wraps ConnectionManager and adds device management features.
    """

    def __init__(self, conn_mgr: ConnectionManager):
        self.conn_mgr = conn_mgr
        self.groups: Dict[str, DeviceGroup] = {}
        self.polling_interval = PollingInterval.MANUAL
        self._polling_task: Optional[asyncio.Task] = None
        self._last_poll: Optional[datetime] = None
        self._polling_stats = {
            "total_polls": 0,
            "successful_polls": 0,
            "failed_polls": 0,
            "last_poll_duration": 0.0
        }
        self.twamp_engine = TWAMPEngine()
        self._twamp_data: Dict[str, List[Any]] = {}  # Store TWAMP data per device
        self._twamp_subscribers: List[Callable] = []  # Subscribers for TWAMP updates

    def create_group(self, name: str, description: str = "") -> DeviceGroup:
        """Create a new device group."""
        if name in self.groups:
            logger.warning("group_exists", group=name)
            return self.groups[name]

        group = DeviceGroup(name, description)
        self.groups[name] = group
        logger.info("group_created", group=name)
        return group

    def delete_group(self, name: str) -> None:
        """Delete a device group."""
        if name in self.groups:
            del self.groups[name]
            logger.info("group_deleted", group=name)

    def add_device_to_group(self, group_name: str, host: str) -> bool:
        """Add a device to a group."""
        group = self.groups.get(group_name)
        if not group:
            logger.error("group_not_found", group=group_name)
            return False

        group.add_device(host)
        logger.info("device_added_to_group", device=host, group=group_name)
        return True

    def remove_device_from_group(self, group_name: str, host: str) -> bool:
        """Remove a device from a group."""
        group = self.groups.get(group_name)
        if not group:
            return False

        group.remove_device(host)
        logger.info("device_removed_from_group", device=host, group=group_name)
        return True

    def add_interface_to_monitor(self, group_name: str, host: str, interface: str) -> bool:
        """Add an interface to monitoring for a device in a group."""
        group = self.groups.get(group_name)
        if not group:
            return False

        group.add_interface(host, interface)
        logger.info("interface_added", device=host, interface=interface, group=group_name)
        return True

    def remove_interface_from_monitoring(self, group_name: str, host: str, interface: str) -> bool:
        """Remove an interface from monitoring."""
        group = self.groups.get(group_name)
        if not group:
            return False

        group.remove_interface(host, interface)
        logger.info("interface_removed", device=host, interface=interface, group=group_name)
        return True

    def get_monitored_interfaces(self, host: str) -> Set[str]:
        """Get all monitored interfaces for a device across all groups."""
        interfaces = set()
        for group in self.groups.values():
            interfaces.update(group.get_interfaces(host))
        return interfaces

    async def set_polling_interval(self, interval: PollingInterval) -> None:
        """Set the polling interval."""
        self.polling_interval = interval

        # Stop existing polling task
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        # Start new polling if not manual
        if interval != PollingInterval.MANUAL:
            self._polling_task = asyncio.create_task(self._run_polling())

        logger.info("polling_interval_set", interval=interval.name, seconds=interval.value)

    async def _run_polling(self) -> None:
        """Run the polling loop."""
        while True:
            try:
                await self.poll_all_devices()
                await asyncio.sleep(self.polling_interval.value)
            except asyncio.CancelledError:
                logger.info("polling_cancelled")
                break
            except Exception as e:
                logger.error("polling_error", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry

    async def poll_all_devices(self) -> Dict[str, Any]:
        """Poll all connected devices and gather data."""
        self._last_poll = datetime.now()
        poll_start = datetime.now()

        results = {
            "success": [],
            "failed": [],
            "data": {}
        }

        self._polling_stats["total_polls"] += 1

        for host, session in self.conn_mgr.sessions.items():
            if session.state != ConnectionState.CONNECTED:
                continue

            try:
                # Get device facts
                facts = await self._get_device_facts(session)

                # Get interface information
                interfaces = await self._get_interface_diagnostics(session)

                # Get monitored interfaces only if specified
                monitored = self.get_monitored_interfaces(host)
                if monitored:
                    interfaces = {k: v for k, v in interfaces.items() if k in monitored}

                results["success"].append(host)
                results["data"][host] = {
                    "facts": facts,
                    "interfaces": interfaces,
                    "timestamp": datetime.now().isoformat()
                }

                self._polling_stats["successful_polls"] += 1

            except Exception as e:
                logger.error("device_poll_failed", device=host, error=str(e))
                results["failed"].append(host)
                self._polling_stats["failed_polls"] += 1

        # Fetch TWAMP data from all connected devices
        await self._poll_twamp_data()

        # Calculate poll duration
        duration = (datetime.now() - poll_start).total_seconds()
        self._polling_stats["last_poll_duration"] = duration

        logger.info(
            "poll_completed",
            success_count=len(results["success"]),
            failed_count=len(results["failed"]),
            duration=duration
        )

        return results

    async def _get_device_facts(self, session: DeviceSession) -> Dict[str, Any]:
        """Get device facts."""
        try:
            loop = asyncio.get_event_loop()
            facts = await loop.run_in_executor(None, lambda: session.dev.facts)
            return facts if isinstance(facts, dict) else {}
        except Exception as e:
            logger.error("facts_fetch_failed", device=session.host, error=str(e))
            return {}

    async def _get_interface_diagnostics(self, session: DeviceSession) -> Dict[str, Any]:
        """Get interface diagnostics including optics, errors, and stats."""
        interfaces = {}

        try:
            # Get interface diagnostics using RPC
            rpc_command = "get-interface-information"
            result = await session.rpc(rpc_command)

            if result and "interface-information" in result:
                phys_interface = result["interface-information"].get("physical-interface", [])

                # Handle single interface case
                if not isinstance(phys_interface, list):
                    phys_interface = [phys_interface]

                for intf in phys_interface:
                    name = intf.get("name", "")
                    if not name:
                        continue

                    # Only monitor optical interfaces (xe-, et-, ge-)
                    if not any(name.startswith(prefix) for prefix in ["xe-", "et-", "ge-"]):
                        continue

                    interfaces[name] = {
                        "description": intf.get("description", ""),
                        "admin_status": intf.get("admin-status", ""),
                        "oper_status": intf.get("oper-status", ""),
                        "optics": self._extract_optics_info(intf),
                        "stats": self._extract_interface_stats(intf)
                    }

        except Exception as e:
            logger.error("interface_diagnostics_failed", device=session.host, error=str(e))

        return interfaces

    def _extract_optics_info(self, intf: Dict) -> Dict[str, Any]:
        """Extract optical diagnostics from interface data."""
        optics = {}

        try:
            optics_info = intf.get("optics-diagnostics", {})
            if optics_info:
                optics = {
                    "laser_output_power": optics_info.get("laser-output-power"),
                    "laser_output_power-dbm": optics_info.get("laser-output-power-dbm"),
                    "laser_bias_current": optics_info.get("laser-bias-current"),
                    "module_temperature": optics_info.get("module-temperature"),
                    "rx_optical_power": optics_info.get("optical-power-rx"),
                    "rx_optical_power-dbm": optics_info.get("optical-power-rx-dbm"),
                }
        except Exception as e:
            logger.debug("optics_extract_failed", error=str(e))

        return optics

    def _extract_interface_stats(self, intf: Dict) -> Dict[str, Any]:
        """Extract interface statistics."""
        stats = {}

        try:
            if_stats = intf.get("interface-flapped", {})
            traffic_stats = intf.get("traffic-statistics", {})

            stats = {
                "flaps": if_stats.get("flap-count", "0"),
                "input_errors": traffic_stats.get("input-errors", "0"),
                "output_errors": traffic_stats.get("output-errors", "0"),
                "crc_errors": traffic_stats.get("crc-errors", "0"),
                "input_bytes": traffic_stats.get("input-bytes", "0"),
                "output_bytes": traffic_stats.get("output-bytes", "0"),
            }
        except Exception as e:
            logger.debug("stats_extract_failed", error=str(e))

        return stats

    async def _poll_twamp_data(self) -> None:
        """Poll TWAMP data from all connected devices."""
        print("[DEBUG] _poll_twamp_data called")
        self._twamp_data = {}

        for host, session in self.conn_mgr.sessions.items():
            if session.state != ConnectionState.CONNECTED:
                print(f"[DEBUG] Skipping {host} - not connected")
                continue

            try:
                print(f"[DEBUG] Fetching TWAMP from {host}")
                # Fetch TWAMP data using the TWAMP engine
                twamp_metrics = await self.twamp_engine.fetch_twamp_data(session)

                if twamp_metrics:
                    self._twamp_data[host] = twamp_metrics
                    print(f"[DEBUG] Got {len(twamp_metrics)} metrics from {host}")
                    logger.info("twamp_data_fetched", device=host, probe_count=len(twamp_metrics))

                    # Notify subscribers about TWAMP updates
                    await self._notify_twamp_subscribers(host, twamp_metrics)
                else:
                    print(f"[DEBUG] No TWAMP metrics returned from {host}")

            except Exception as e:
                print(f"[ERROR] Failed to poll TWAMP from {host}: {e}")
                logger.error("twamp_poll_failed", device=host, error=str(e))

        print(f"[DEBUG] _poll_twamp_data complete. _twamp_data keys: {list(self._twamp_data.keys())}")

    async def _notify_twamp_subscribers(self, host: str, twamp_metrics: List[Any]) -> None:
        """Notify subscribers about TWAMP data updates."""
        for callback in self._twamp_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(host, twamp_metrics)
                else:
                    callback(host, twamp_metrics)
            except Exception as e:
                logger.error("twamp_subscriber_error", error=str(e))

    def subscribe_to_twamp_updates(self, callback: Callable[[str, List[Any]], Any]) -> None:
        """Subscribe to TWAMP data updates."""
        if callback not in self._twamp_subscribers:
            self._twamp_subscribers.append(callback)

    def unsubscribe_from_twamp_updates(self, callback: Callable[[str, List[Any]], Any]) -> None:
        """Unsubscribe from TWAMP data updates."""
        if callback in self._twamp_subscribers:
            self._twamp_subscribers.remove(callback)

    def get_twamp_data(self, host: Optional[str] = None) -> Dict[str, List[Any]]:
        """Get TWAMP data for a specific host or all hosts."""
        if host:
            return self._twamp_data.get(host, [])
        return self._twamp_data

    def get_all_twamp_metrics(self) -> List[Any]:
        """Get all TWAMP metrics from all devices as a flat list."""
        all_metrics = []
        for metrics_list in self._twamp_data.values():
            all_metrics.extend(metrics_list)
        return all_metrics

    async def fetch_device_data(self, host: str) -> Optional[Dict[str, Any]]:
        """Fetch data for a single device."""
        session = self.conn_mgr.sessions.get(host)
        if not session or session.state != ConnectionState.CONNECTED:
            logger.warning("device_not_connected", device=host)
            return None

        try:
            facts = await self._get_device_facts(session)
            interfaces = await self._get_interface_diagnostics(session)

            # Filter by monitored interfaces
            monitored = self.get_monitored_interfaces(host)
            if monitored:
                interfaces = {k: v for k, v in interfaces.items() if k in monitored}

            return {
                "facts": facts,
                "interfaces": interfaces,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("device_data_fetch_failed", device=host, error=str(e))
            return None

    def get_device_counts(self) -> Dict[str, int]:
        """Get device connection counts."""
        total = len(self.conn_mgr.sessions)
        connected = sum(
            1 for s in self.conn_mgr.sessions.values()
            if s.state == ConnectionState.CONNECTED
        )
        failed = sum(
            1 for s in self.conn_mgr.sessions.values()
            if s.state == ConnectionState.FAILED
        )

        return {
            "total": total,
            "connected": connected,
            "failed": failed
        }

    def get_polling_stats(self) -> Dict[str, Any]:
        """Get polling statistics."""
        return {
            **self._polling_stats,
            "last_poll": self._last_poll.isoformat() if self._last_poll else None,
            "interval": self.polling_interval.name
        }

    async def subscribe_to_events(self, callback: Callable[[EventMessage], Any]) -> None:
        """Subscribe to connection manager events."""
        await self.conn_mgr.subscribe_to_events(callback)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
