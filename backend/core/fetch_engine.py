"""
fetch_engine.py
───────────────
PyEZ-based data fetching engine for Juniper devices.

Provides methods to fetch various types of information:
- Facts: Device system information
- Routing: Routing table entries
- Interfaces: Interface details and statistics
- Chassis: Hardware and inventory information
- Protocols: OSPF, BGP, LDP
- MPLS: RSVP, LDP
- Optics: Optical diagnostics and transceivers
- All: Fetch all above information
"""

import asyncio
from typing import Dict, List, Any, Optional
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from backend.core.connection_engine import ConnectionManager, DeviceSession
from backend.utils.logging import logger


class FetchEngine:
    """
    Fetches data from Juniper devices using PyEZ.

    All methods return JSON-serializable dictionaries with:
    - status: "success" or "error"
    - data: fetched data (on success)
    - error: error message (on failure)
    - timestamp: ISO format timestamp
    """

    def __init__(self, conn_manager: ConnectionManager):
        self.conn_manager = conn_manager

    async def fetch_facts(self, host: str) -> Dict[str, Any]:
        """
        Fetch device facts (hostname, model, serial, OS version, uptime).

        Returns:
            Dict with device facts
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get facts from device
            facts = await loop.run_in_executor(None, lambda: session.dev.facts)

            result = {
                "status": "success",
                "data": {
                    "hostname": facts.get("hostname", "N/A"),
                    "model": facts.get("model", "N/A"),
                    "serial": facts.get("serialnumber", "N/A"),
                    "version": facts.get("version", "N/A"),
                    "os_version": facts.get("junos_version", "N/A"),
                    "hostname": facts.get("hostname", "N/A"),
                    "uptime": self._format_uptime(facts.get("uptime", 0)),
                    "switch_style": facts.get("switch_style", "N/A"),
                    "vc_mode": facts.get("vc_mode", "N/A"),
                    "personality": facts.get("personality", "N/A"),
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_facts_success", device=host)
            return result

        except Exception as e:
            logger.error("fetch_facts_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_interfaces(self, host: str) -> Dict[str, Any]:
        """
        Fetch interface information (status, stats, optics).

        Returns:
            Dict with interface data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get interface information via RPC
            rpc_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_interface_information(
                    extensive=True,
                    normalize=True
                )
            )

            interfaces = []
            for intf in rpc_reply.findall(".//physical-interface"):
                name = intf.findtext("name")
                if not name:
                    continue

                # Basic info
                admin_status = intf.findtext("admin-status")
                oper_status = intf.findtext("oper-status")

                # Statistics
                stats = intf.find("interface-statistics")
                rx_bytes = stats.findtext("input-bytes") if stats is not None else "N/A"
                tx_bytes = stats.findtext("output-bytes") if stats is not None else "N/A"
                rx_packets = stats.findtext("input-packets") if stats is not None else "N/A"
                tx_packets = stats.findtext("output-packets") if stats is not None else "N/A"
                errors = stats.findtext("input-errors") if stats is not None else "0"

                # Optics
                optics = intf.find("optic-attributes")
                rx_power = optics.findtext("optics-diagnostics/rx-optical-power-dbm") if optics is not None else "N/A"
                tx_power = optics.findtext("optics-diagnostics/tx-optical-power-dbm") if optics is not None else "N/A"
                temp = optics.findtext("optics-diagnostics/module-temperature") if optics is not None else "N/A"

                interfaces.append({
                    "name": name,
                    "description": intf.findtext("description") or "",
                    "admin_status": admin_status or "unknown",
                    "oper_status": oper_status or "unknown",
                    "mac_address": intf.findtext("current-physical-address") or "N/A",
                    "mtu": intf.findtext("mtu") or "N/A",
                    "speed": intf.findtext("speed") or "N/A",
                    "rx_bytes": rx_bytes,
                    "tx_bytes": tx_bytes,
                    "rx_packets": rx_packets,
                    "tx_packets": tx_packets,
                    "errors": errors,
                    "rx_power_dbm": rx_power,
                    "tx_power_dbm": tx_power,
                    "temperature": temp,
                })

            result = {
                "status": "success",
                "data": {
                    "interfaces": interfaces,
                    "count": len(interfaces)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_interfaces_success", device=host, count=len(interfaces))
            return result

        except Exception as e:
            logger.error("fetch_interfaces_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_routing_table(self, host: str) -> Dict[str, Any]:
        """
        Fetch routing table (IPv4 and IPv6 routes).

        Returns:
            Dict with routing table data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get IPv4 routes
            ipv4_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_route_information(
                    table="inet.0",
                    normalize=True
                )
            )

            routes = []
            for rt in ipv4_reply.findall(".//route"):
                dest = rt.findtext("destination-prefix")
                next_hop = rt.findtext("next-hop/next-hop-address")
                proto = rt.findtext("protocol-name")
                age = rt.findtext("age") or "0"
                pref = rt.findtext("preference") or "0"

                if dest:
                    routes.append({
                        "destination": dest,
                        "next_hop": next_hop or "N/A",
                        "protocol": proto or "N/A",
                        "age_seconds": age,
                        "preference": pref,
                        "table": "inet.0"
                    })

            result = {
                "status": "success",
                "data": {
                    "routes": routes[:100],  # Limit to first 100
                    "count": len(routes),
                    "table": "inet.0"
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_routing_success", device=host, count=len(routes))
            return result

        except Exception as e:
            logger.error("fetch_routing_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_chassis(self, host: str) -> Dict[str, Any]:
        """
        Fetch chassis hardware and inventory information.

        Returns:
            Dict with chassis data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get hardware info
            hw_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_chassis_inventory(
                    extensive=True,
                    normalize=True
                )
            )

            chassis_data = []

            # Parse chassis hierarchy
            for chassis in hw_reply.findall(".//chassis"):
                chassis_name = chassis.findtext("name")
                serial_num = chassis.findtext("serial-number")
                part_num = chassis.findtext("part-number")

                chassis_data.append({
                    "type": "chassis",
                    "name": chassis_name or "N/A",
                    "serial": serial_num or "N/A",
                    "part_number": part_num or "N/A",
                    "description": chassis.findtext("description") or ""
                })

                # Get FPCs
                for fpc in chassis.findall(".//fpc"):
                    fpc_name = fpc.findtext("name")
                    fpc_serial = fpc.findtext("serial-number")
                    fpc_state = fpc.findtext("state")

                    chassis_data.append({
                        "type": "fpc",
                        "name": fpc_name or "N/A",
                        "serial": fpc_serial or "N/A",
                        "state": fpc_state or "unknown",
                        "description": fpc.findtext("description") or ""
                    })

            result = {
                "status": "success",
                "data": {
                    "hardware": chassis_data,
                    "count": len(chassis_data)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_chassis_success", device=host)
            return result

        except Exception as e:
            logger.error("fetch_chassis_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_ospf(self, host: str) -> Dict[str, Any]:
        """
        Fetch OSPF neighbor information.

        Returns:
            Dict with OSPF data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get OSPF neighbors
            ospf_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_ospf_neighbor_information(
                    normalize=True
                )
            )

            neighbors = []
            for neighbor in ospf_reply.findall(".//ospf-neighbor"):
                neighbors.append({
                    "interface": neighbor.findtext("interface-name") or "N/A",
                    "neighbor_id": neighbor.findtext("neighbor-id") or "N/A",
                    "state": neighbor.findtext("ospf-neighbor-state") or "unknown",
                    "priority": neighbor.findtext("neighbor-priority") or "0",
                    "dead_time": neighbor.findtext("neighbor-dead-time") or "N/A",
                })

            result = {
                "status": "success",
                "data": {
                    "neighbors": neighbors,
                    "count": len(neighbors)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_ospf_success", device=host, count=len(neighbors))
            return result

        except Exception as e:
            logger.error("fetch_ospf_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_bgp(self, host: str) -> Dict[str, Any]:
        """
        Fetch BGP neighbor information.

        Returns:
            Dict with BGP data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get BGP summary
            bgp_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_bgp_summary_information(
                    normalize=True
                )
            )

            peers = []
            for peer in bgp_reply.findall(".//bgp-peer"):
                peers.append({
                    "peer_address": peer.findtext("peer-address") or "N/A",
                    "peer_as": peer.findtext("peer-as") or "N/A",
                    "state": peer.findtext("peer-state") or "unknown",
                    "flap_count": peer.findtext("flap-count") or "0",
                    "elapsed_time": peer.findtext("elapsed-time") or "N/A",
                    "input_messages": peer.findtext("input-messages") or "0",
                    "output_messages": peer.findtext("output-messages") or "0",
                })

            result = {
                "status": "success",
                "data": {
                    "peers": peers,
                    "count": len(peers)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_bgp_success", device=host, count=len(peers))
            return result

        except Exception as e:
            logger.error("fetch_bgp_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_ldp(self, host: str) -> Dict[str, Any]:
        """
        Fetch LDP neighbor and session information.

        Returns:
            Dict with LDP data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get LDP neighbors
            ldp_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_ldp_neighbor_information(
                    normalize=True
                )
            )

            neighbors = []
            for neighbor in ldp_reply.findall(".//ldp-neighbor"):
                neighbors.append({
                    "interface": neighbor.findtext("ldp-interface-name") or "N/A",
                    "neighbor_address": neighbor.findtext("ldp-neighbor-address") or "N/A",
                    "state": neighbor.findtext("ldp-neighbor-state") or "unknown",
                    "held_time": neighbor.findtext("ldp-neighbor-hold-time") or "N/A",
                })

            result = {
                "status": "success",
                "data": {
                    "neighbors": neighbors,
                    "count": len(neighbors)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_ldp_success", device=host, count=len(neighbors))
            return result

        except Exception as e:
            logger.error("fetch_ldp_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_rsvp(self, host: str) -> Dict[str, Any]:
        """
        Fetch RSVP session information.

        Returns:
            Dict with RSVP data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get RSVP sessions
            rsvp_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_rsvp_session_information(
                    normalize=True
                )
            )

            sessions = []
            for session in rsvp_reply.findall(".//rsvp-session"):
                sessions.append({
                    "destination": session.findtext("session-name") or "N/A",
                    "source": session.findtext("source-address") or "N/A",
                    "lsp_state": session.findtext("lsp-state") or "unknown",
                    "count": session.findtext("packet-count") or "0",
                })

            result = {
                "status": "success",
                "data": {
                    "sessions": sessions,
                    "count": len(sessions)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_rsvp_success", device=host, count=len(sessions))
            return result

        except Exception as e:
            logger.error("fetch_rsvp_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_optics(self, host: str) -> Dict[str, Any]:
        """
        Fetch optical diagnostics and transceiver information.

        Returns:
            Dict with optics data
        """
        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "status": "error",
                "error": "Device not connected",
                "timestamp": self._get_timestamp()
            }

        try:
            loop = asyncio.get_event_loop()

            # Get interface optics (extensive for transceiver info)
            optics_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_interface_optics_diagnostics_information(
                    normalize=True
                )
            )

            optics_list = []
            for intf in optics_reply.findall(".//physical-interface"):
                name = intf.findtext("name")
                if not name:
                    continue

                # Get optics diagnostics
                diag = intf.find("optics-diagnostics")
                if diag is not None:
                    optics_list.append({
                        "interface": name,
                        "laser_bias_current": diag.findtext("laser-bias-current") or "N/A",
                        "laser_output_power": diag.findtext("laser-output-power-dbm") or "N/A",
                        "laser_output_power-dbm": diag.findtext("laser-output-power-dbm") or "N/A",
                        "rx_optical_power": diag.findtext("rx-optical-power-dbm") or "N/A",
                        "module_temperature": diag.findtext("module-temperature") or "N/A",
                        "module_voltage": diag.findtext("module-voltage") or "N/A",
                        "tx_dwdm_freq": diag.findtext("tx-dwdm-frequency") or "N/A",
                    })

            # Get transceiver information (SFP/QSFP modules)
            xcvr_reply = await loop.run_in_executor(
                None,
                lambda: session.dev.rpc.get_transceiver_information(
                    normalize=True
                )
            )

            transceivers = []
            for xcvr in xcvr_reply.findall(".//transceiver-information"):
                transceivers.append({
                    "interface": xcvr.findtext("name") or "N/A",
                    "type": xcvr.findtext("transceiver-type") or "N/A",
                    "vendor": xcvr.findtext("vendor-name") or "N/A",
                    "part_number": xcvr.findtext("part-number") or "N/A",
                    "serial_number": xcvr.findtext("serial-number") or "N/A",
                })

            result = {
                "status": "success",
                "data": {
                    "optics": optics_list,
                    "transceivers": transceivers,
                    "optics_count": len(optics_list),
                    "transceiver_count": len(transceivers)
                },
                "timestamp": self._get_timestamp()
            }
            logger.info("fetch_optics_success", device=host)
            return result

        except Exception as e:
            logger.error("fetch_optics_error", device=host, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    async def fetch_all(self, host: str) -> Dict[str, Any]:
        """
        Fetch all information types from a device.

        Returns:
            Dict with all fetch results grouped by type
        """
        logger.info("fetch_all_start", device=host)

        results = {
            "device": host,
            "timestamp": self._get_timestamp(),
            "fetches": {}
        }

        # Fetch all types in parallel
        tasks = {
            "facts": self.fetch_facts(host),
            "interfaces": self.fetch_interfaces(host),
            "routing": self.fetch_routing_table(host),
            "chassis": self.fetch_chassis(host),
            "ospf": self.fetch_ospf(host),
            "bgp": self.fetch_bgp(host),
            "ldp": self.fetch_ldp(host),
            "rsvp": self.fetch_rsvp(host),
            "optics": self.fetch_optics(host),
        }

        # Execute all tasks
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (fetch_type, result), exception in zip(tasks.items(), completed):
            if isinstance(exception, Exception):
                results["fetches"][fetch_type] = {
                    "status": "error",
                    "error": str(exception)
                }
            else:
                results["fetches"][fetch_type] = result

        logger.info("fetch_all_complete", device=host)
        return results

    def _get_timestamp(self) -> str:
        """Get current ISO format timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _format_uptime(self, uptime_seconds: int) -> str:
        """Format uptime seconds to human-readable string."""
        if uptime_seconds == 0:
            return "N/A"

        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "0m"
