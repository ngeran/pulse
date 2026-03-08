import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from backend.core.connection_engine import ConnectionManager, DeviceSession
from backend.utils.logging import logger
from jnpr.junos import Device
from jnpr.junos.factory.factory_loader import FactoryLoader
import yaml
import os

# Load PyEZ definitions
with open(os.path.join(os.path.dirname(__file__), "interface_def.yaml"), "r") as f:
    _definitions = yaml.safe_load(f)
    globals().update(FactoryLoader().load(_definitions))

# BGP and ARP table definitions (inline to avoid separate files)
BGP_DEF = """
BgpTable:
  rpc: get-bgp-summary-information
  item: bgp-peer
  view: BgpView

BgpView:
  fields:
    peer_address: peer-address
    peer_as: peer-as
    state: peer-state
    flap_count: flap-count
    elapsed_time: elapsed-time
"""

ARP_DEF = """
ArpTable:
  rpc: get-arp-table-information
  item: arp-table-entry
  view: ArpView

ArpView:
  fields:
    ip_address: ip-address
    mac_address: mac-address
    interface: interface-name
"""

# Load BGP and ARP tables
_bgp_def = yaml.safe_load(BGP_DEF)
globals().update(FactoryLoader().load(_bgp_def))

_arp_def = yaml.safe_load(ARP_DEF)
globals().update(FactoryLoader().load(_arp_def))

class InterfaceDiscovery:
    def __init__(self, conn_manager: ConnectionManager, cache_ttl: int = 300):
        self.conn_manager = conn_manager
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.bgp_cache: Dict[str, Dict[str, Any]] = {}
        self.arp_cache: Dict[str, Dict[str, Any]] = {}

    async def get_interfaces(self, host: str) -> Dict[str, Any]:
        now = time.time()
        if host in self.cache:
            entry = self.cache[host]
            if now - entry["discovery_time_unix"] < self.cache_ttl:
                return entry

        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "interfaces": [],
                "discovery_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "failed",
                "error": "Device not connected"
            }

        try:
            loop = asyncio.get_event_loop()
            # Run table fetch in executor
            table = InterfaceTable(session.dev)
            data = await loop.run_in_executor(None, table.get)
            
            interfaces = []
            for item in data:
                name = item.name
                # Filtering for xe-, et-, ge-
                if any(name.startswith(p) for p in ["xe-", "et-", "ge-"]):
                    interfaces.append({
                        "name": name,
                        "description": item.description or "",
                        "admin_status": item.admin_status,
                        "oper_status": item.oper_status
                    })

            result = {
                "interfaces": interfaces,
                "discovery_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "discovery_time_unix": now,
                "status": "success"
            }
            self.cache[host] = result
            return result
        except Exception as e:
            logger.error("discovery_failed", device=host, error=str(e))
            return {
                "interfaces": [],
                "discovery_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "failed",
                "error": str(e)
            }

    async def discover_all(self, hosts: List[str]) -> Dict[str, Any]:
        tasks = [self.get_interfaces(host) for host in hosts]
        results = await asyncio.gather(*tasks)

        aggregated = {}
        for host, res in zip(hosts, results):
            aggregated[host] = res

        return aggregated

    async def get_bgp_neighbors(self, host: str) -> Dict[str, Any]:
        """Get BGP neighbor information for a device."""
        now = time.time()
        if host in self.bgp_cache:
            entry = self.bgp_cache[host]
            if now - entry["discovery_time_unix"] < self.cache_ttl:
                return entry

        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "neighbors": [],
                "discovery_time": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "error": "Device not connected"
            }

        try:
            loop = asyncio.get_event_loop()
            table = BgpTable(session.dev)
            data = await loop.run_in_executor(None, table.get)

            neighbors = []
            for item in data:
                neighbors.append({
                    "peer_address": getattr(item, 'peer_address', 'N/A'),
                    "peer_as": getattr(item, 'peer_as', 0),
                    "state": getattr(item, 'state', 'Unknown'),
                    "flap_count": getattr(item, 'flap_count', 0),
                    "elapsed_time": getattr(item, 'elapsed_time', 'N/A')
                })

            result = {
                "neighbors": neighbors,
                "discovery_time": datetime.now(timezone.utc).isoformat(),
                "discovery_time_unix": now,
                "status": "success"
            }
            self.bgp_cache[host] = result
            return result
        except Exception as e:
            logger.error("bgp_discovery_failed", device=host, error=str(e))
            return {
                "neighbors": [],
                "discovery_time": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "error": str(e)
            }

    async def get_arp_table(self, host: str) -> Dict[str, Any]:
        """Get ARP table information for a device."""
        now = time.time()
        if host in self.arp_cache:
            entry = self.arp_cache[host]
            if now - entry["discovery_time_unix"] < self.cache_ttl:
                return entry

        session = self.conn_manager.sessions.get(host)
        if not session or session.state.value != "CONNECTED":
            return {
                "entries": [],
                "entry_count": 0,
                "discovery_time": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "error": "Device not connected"
            }

        try:
            loop = asyncio.get_event_loop()
            table = ArpTable(session.dev)
            data = await loop.run_in_executor(None, table.get)

            entries = []
            for item in data:
                entries.append({
                    "ip_address": getattr(item, 'ip_address', 'N/A'),
                    "mac_address": getattr(item, 'mac_address', 'N/A'),
                    "interface": getattr(item, 'interface', 'N/A')
                })

            result = {
                "entries": entries,
                "entry_count": len(entries),
                "discovery_time": datetime.now(timezone.utc).isoformat(),
                "discovery_time_unix": now,
                "status": "success"
            }
            self.arp_cache[host] = result
            return result
        except Exception as e:
            logger.error("arp_discovery_failed", device=host, error=str(e))
            return {
                "entries": [],
                "entry_count": 0,
                "discovery_time": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "error": str(e)
            }

    async def discover_bgp_all(self, hosts: List[str]) -> Dict[str, Any]:
        """Get BGP information for all hosts."""
        tasks = [self.get_bgp_neighbors(host) for host in hosts]
        results = await asyncio.gather(*tasks)

        aggregated = {}
        for host, res in zip(hosts, results):
            aggregated[host] = res

        return aggregated

    async def discover_arp_all(self, hosts: List[str]) -> Dict[str, Any]:
        """Get ARP information for all hosts."""
        tasks = [self.get_arp_table(host) for host in hosts]
        results = await asyncio.gather(*tasks)

        aggregated = {}
        for host, res in zip(hosts, results):
            aggregated[host] = res

        return aggregated
