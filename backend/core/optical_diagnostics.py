"""
optical_diagnostics.py
──────────────────────
Optical diagnostics collector using PyEZ.

Fetches and parses optical diagnostics and interface statistics
from Juniper devices using JSON RPC.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.connection_engine import DeviceSession
from backend.utils.logging import logger


class OpticalDiagnostics:
    """
    Optical diagnostics data for an interface.
    """

    def __init__(
        self,
        interface_name: str,
        laser_output_power: float,
        laser_output_power_dbm: float,
        rx_signal_power: float,
        rx_signal_power_dbm: float,
        module_temperature: float,
        laser_bias_current: float,
        module_voltage: float,
        tx_power_high_alarm: bool = False,
        tx_power_low_alarm: bool = False,
        tx_power_high_warn: bool = False,
        tx_power_low_warn: bool = False,
        rx_power_high_alarm: bool = False,
        rx_power_low_alarm: bool = False,
        rx_power_high_warn: bool = False,
        rx_power_low_warn: bool = False,
        temp_high_alarm: bool = False,
        temp_low_alarm: bool = False,
        temp_high_warn: bool = False,
        temp_low_warn: bool = False,
        bias_high_alarm: bool = False,
        bias_low_alarm: bool = False,
        bias_high_warn: bool = False,
        bias_low_warn: bool = False,
        # Alarm thresholds
        tx_power_high_alarm_threshold: Optional[float] = None,
        tx_power_low_alarm_threshold: Optional[float] = None,
        tx_power_high_warn_threshold: Optional[float] = None,
        tx_power_low_warn_threshold: Optional[float] = None,
        rx_power_high_alarm_threshold: Optional[float] = None,
        rx_power_low_alarm_threshold: Optional[float] = None,
        rx_power_high_warn_threshold: Optional[float] = None,
        rx_power_low_warn_threshold: Optional[float] = None,
        temp_high_alarm_threshold: Optional[float] = None,
        temp_low_alarm_threshold: Optional[float] = None,
        temp_high_warn_threshold: Optional[float] = None,
        temp_low_warn_threshold: Optional[float] = None,
        bias_high_alarm_threshold: Optional[float] = None,
        bias_low_alarm_threshold: Optional[float] = None,
        bias_high_warn_threshold: Optional[float] = None,
        bias_low_warn_threshold: Optional[float] = None,
    ):
        self.interface_name = interface_name
        self.laser_output_power = laser_output_power
        self.laser_output_power_dbm = laser_output_power_dbm
        self.rx_signal_power = rx_signal_power
        self.rx_signal_power_dbm = rx_signal_power_dbm
        self.module_temperature = module_temperature
        self.laser_bias_current = laser_bias_current
        self.module_voltage = module_voltage

        # Alarm states
        self.tx_power_high_alarm = tx_power_high_alarm
        self.tx_power_low_alarm = tx_power_low_alarm
        self.tx_power_high_warn = tx_power_high_warn
        self.tx_power_low_warn = tx_power_low_warn
        self.rx_power_high_alarm = rx_power_high_alarm
        self.rx_power_low_alarm = rx_power_low_alarm
        self.rx_power_high_warn = rx_power_high_warn
        self.rx_power_low_warn = rx_power_low_warn
        self.temp_high_alarm = temp_high_alarm
        self.temp_low_alarm = temp_low_alarm
        self.temp_high_warn = temp_high_warn
        self.temp_low_warn = temp_low_warn
        self.bias_high_alarm = bias_high_alarm
        self.bias_low_alarm = bias_low_alarm
        self.bias_high_warn = bias_high_warn
        self.bias_low_warn = bias_low_warn

        # Alarm thresholds
        self.tx_power_high_alarm_threshold = tx_power_high_alarm_threshold
        self.tx_power_low_alarm_threshold = tx_power_low_alarm_threshold
        self.tx_power_high_warn_threshold = tx_power_high_warn_threshold
        self.tx_power_low_warn_threshold = tx_power_low_warn_threshold
        self.rx_power_high_alarm_threshold = rx_power_high_alarm_threshold
        self.rx_power_low_alarm_threshold = rx_power_low_alarm_threshold
        self.rx_power_high_warn_threshold = rx_power_high_warn_threshold
        self.rx_power_low_warn_threshold = rx_power_low_warn_threshold
        self.temp_high_alarm_threshold = temp_high_alarm_threshold
        self.temp_low_alarm_threshold = temp_low_alarm_threshold
        self.temp_high_warn_threshold = temp_high_warn_threshold
        self.temp_low_warn_threshold = temp_low_warn_threshold
        self.bias_high_alarm_threshold = bias_high_alarm_threshold
        self.bias_low_alarm_threshold = bias_low_alarm_threshold
        self.bias_high_warn_threshold = bias_high_warn_threshold
        self.bias_low_warn_threshold = bias_low_warn_threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "interface_name": self.interface_name,
            "laser_output_power": self.laser_output_power,
            "laser_output_power_dbm": self.laser_output_power_dbm,
            "rx_signal_power": self.rx_signal_power,
            "rx_signal_power_dbm": self.rx_signal_power_dbm,
            "module_temperature": self.module_temperature,
            "laser_bias_current": self.laser_bias_current,
            "module_voltage": self.module_voltage,
            "tx_power_high_alarm": self.tx_power_high_alarm,
            "tx_power_low_alarm": self.tx_power_low_alarm,
            "tx_power_high_warn": self.tx_power_high_warn,
            "tx_power_low_warn": self.tx_power_low_warn,
            "rx_power_high_alarm": self.rx_power_high_alarm,
            "rx_power_low_alarm": self.rx_power_low_alarm,
            "rx_power_high_warn": self.rx_power_high_warn,
            "rx_power_low_warn": self.rx_power_low_warn,
            "temp_high_alarm": self.temp_high_alarm,
            "temp_low_alarm": self.temp_low_alarm,
            "temp_high_warn": self.temp_high_warn,
            "temp_low_warn": self.temp_low_warn,
            "bias_high_alarm": self.bias_high_alarm,
            "bias_low_alarm": self.bias_low_alarm,
            "bias_high_warn": self.bias_high_warn,
            "bias_low_warn": self.bias_low_warn,
            "tx_power_high_alarm_threshold": self.tx_power_high_alarm_threshold,
            "tx_power_low_alarm_threshold": self.tx_power_low_alarm_threshold,
            "tx_power_high_warn_threshold": self.tx_power_high_warn_threshold,
            "tx_power_low_warn_threshold": self.tx_power_low_warn_threshold,
            "rx_power_high_alarm_threshold": self.rx_power_high_alarm_threshold,
            "rx_power_low_alarm_threshold": self.rx_power_low_alarm_threshold,
            "rx_power_high_warn_threshold": self.rx_power_high_warn_threshold,
            "rx_power_low_warn_threshold": self.rx_power_low_warn_threshold,
            "temp_high_alarm_threshold": self.temp_high_alarm_threshold,
            "temp_low_alarm_threshold": self.temp_low_alarm_threshold,
            "temp_high_warn_threshold": self.temp_high_warn_threshold,
            "temp_low_warn_threshold": self.temp_low_warn_threshold,
            "bias_high_alarm_threshold": self.bias_high_alarm_threshold,
            "bias_low_alarm_threshold": self.bias_low_alarm_threshold,
            "bias_high_warn_threshold": self.bias_high_warn_threshold,
            "bias_low_warn_threshold": self.bias_low_warn_threshold,
        }


class InterfaceStatistics:
    """
    Interface statistics from extensive show command.
    """

    def __init__(
        self,
        interface_name: str,
        admin_status: str,
        oper_status: str,
        description: str = "",
        speed: str = "",
        mtu: int = 1514,
        mac_address: str = "",
        input_bytes: int = 0,
        output_bytes: int = 0,
        input_packets: int = 0,
        output_packets: int = 0,
        input_errors: int = 0,
        output_errors: int = 0,
        input_drops: int = 0,
        output_drops: int = 0,
        input_crc_errors: int = 0,
        output_crc_errors: int = 0,
        carrier_transitions: int = 0,
        interface_flapped: Optional[str] = None,
    ):
        self.interface_name = interface_name
        self.admin_status = admin_status
        self.oper_status = oper_status
        self.description = description
        self.speed = speed
        self.mtu = mtu
        self.mac_address = mac_address
        self.input_bytes = input_bytes
        self.output_bytes = output_bytes
        self.input_packets = input_packets
        self.output_packets = output_packets
        self.input_errors = input_errors
        self.output_errors = output_errors
        self.input_drops = input_drops
        self.output_drops = output_drops
        self.input_crc_errors = input_crc_errors
        self.output_crc_errors = output_crc_errors
        self.carrier_transitions = carrier_transitions
        self.interface_flapped = interface_flapped

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "interface_name": self.interface_name,
            "admin_status": self.admin_status,
            "oper_status": self.oper_status,
            "description": self.description,
            "speed": self.speed,
            "mtu": self.mtu,
            "mac_address": self.mac_address,
            "input_bytes": self.input_bytes,
            "output_bytes": self.output_bytes,
            "input_packets": self.input_packets,
            "output_packets": self.output_packets,
            "input_errors": self.input_errors,
            "output_errors": self.output_errors,
            "input_drops": self.input_drops,
            "output_drops": self.output_drops,
            "input_crc_errors": self.input_crc_errors,
            "output_crc_errors": self.output_crc_errors,
            "carrier_transitions": self.carrier_transitions,
            "interface_flapped": self.interface_flapped,
        }


class OpticalDiagnosticsEngine:
    """
    Engine for collecting optical diagnostics and interface statistics
    from Juniper devices using PyEZ.
    """

    def __init__(self, conn_mgr):
        """
        Initialize the optical diagnostics engine.

        Args:
            conn_mgr: ConnectionManager instance
        """
        self.conn_mgr = conn_mgr

    async def get_optical_diagnostics(
        self, device_name: str, interface: str
    ) -> Optional[OpticalDiagnostics]:
        """
        Fetch optical diagnostics for a specific interface.

        Args:
            device_name: Name of the device
            interface: Interface name (e.g., "ge-0/0/6")

        Returns:
            OpticalDiagnostics object or None if not available
        """
        device_session = self.conn_mgr.sessions.get(device_name)
        if not device_session:
            logger.warning(
                "optical_diagnostics_device_not_found",
                device=device_name,
                interface=interface,
            )
            return None

        try:
            # Run the command via PyEZ CLI (not RPC - use cli() for | display json commands)
            cmd = f"show interfaces diagnostics optics {interface} | display json"
            logger.info("optical_diagnostics_fetching", device=device_name, interface=interface, command=cmd)

            result = await device_session.cli(cmd)

            if not result:
                logger.warning(
                    "optical_diagnostics_no_result",
                    device=device_name,
                    interface=interface,
                    reason="CLI command returned None/empty result"
                )
                return None

            # Check if result is empty or doesn't have expected structure
            if isinstance(result, str) and result.strip() == "":
                logger.warning(
                    "optical_diagnostics_empty_response",
                    device=device_name,
                    interface=interface,
                    reason="CLI command returned empty string"
                )
                return None

            # Log the result type for debugging
            logger.info(
                "optical_diagnostics_result_type",
                device=device_name,
                interface=interface,
                result_type=str(type(result)),
            )

            # If result is a dict, log a sample of keys for debugging
            if isinstance(result, dict):
                logger.info(
                    "optical_diagnostics_response_structure",
                    device=device_name,
                    interface=interface,
                    top_level_keys=list(result.keys())[:10],  # First 10 keys
                )
                # Check if it has the expected structure
                if "interface-information" in result:
                    logger.info(
                        "optical_diagnostics_has_interface_info",
                        device=device_name,
                        interface=interface,
                    )
                else:
                    logger.warning(
                        "optical_diagnostics_unexpected_structure",
                        device=device_name,
                        interface=interface,
                        available_keys=list(result.keys()),
                        hint="Expected 'interface-information' key in response"
                    )

            # Parse the JSON response
            parsed = self._parse_optical_diagnostics(result, interface)
            if parsed:
                logger.info(
                    "optical_diagnostics_parse_success",
                    device=device_name,
                    interface=interface,
                    tx_power=parsed.laser_output_power_dbm,
                    rx_power=parsed.rx_signal_power_dbm,
                    temp=parsed.module_temperature,
                )
            else:
                logger.warning(
                    "optical_diagnostics_parse_failed",
                    device=device_name,
                    interface=interface,
                    reason="_parse_optical_diagnostics returned None",
                )
            return parsed

        except Exception as e:
            logger.error(
                "optical_diagnostics_fetch_failed",
                device=device_name,
                interface=interface,
                error=str(e),
                exc_info=True,
            )
            return None

    def _parse_optical_diagnostics(
        self, rpc_result: Dict, interface: str
    ) -> Optional[OpticalDiagnostics]:
        """
        Parse JSON-RPC response for optical diagnostics.

        Args:
            rpc_result: Raw RPC result from PyEZ
            interface: Interface name

        Returns:
            OpticalDiagnostics object or None if parsing fails
        """
        try:
            # Navigate the JSON structure
            interface_info = rpc_result.get("interface-information", [{}])[0]
            if not interface_info:
                logger.debug(
                    "optical_diagnostics_no_interface_info",
                    interface=interface,
                    keys_in_rpc=list(rpc_result.keys()) if isinstance(rpc_result, dict) else "not_a_dict"
                )
                return None

            physical_interface = interface_info.get("physical-interface", [{}])[0]
            if not physical_interface:
                logger.debug(
                    "optical_diagnostics_no_physical_interface",
                    interface=interface,
                    keys_in_interface_info=list(interface_info.keys()) if isinstance(interface_info, dict) else "not_a_dict"
                )
                return None

            optics = physical_interface.get("optics-diagnostics", [{}])[0]
            if not optics or (isinstance(optics, dict) and len(optics) == 0):
                logger.debug(
                    "optical_diagnostics_not_available",
                    interface=interface,
                    reason="No optics-diagnostics field or empty",
                    available_keys=list(physical_interface.keys()) if isinstance(physical_interface, dict) else "not_a_dict"
                )
                return None

            # Helper function to extract data field
            def get_value(parent: Dict, key: str, default=None):
                items = parent.get(key, [{}])
                if items and isinstance(items, list) and len(items) > 0:
                    data = items[0].get("data", default)
                    if isinstance(data, str):
                        # Try to convert to float
                        try:
                            return float(data)
                        except ValueError:
                            return default
                    return data
                return default

            # Helper to extract alarm state
            def get_alarm_state(parent: Dict, key: str) -> bool:
                items = parent.get(key, [{}])
                if items and isinstance(items, list) and len(items) > 0:
                    state = items[0].get("data", "off")
                    return state.lower() == "on"
                return False

            # Extract main values
            laser_output_power = get_value(optics, "laser-output-power", 0.0)
            laser_output_power_dbm = get_value(optics, "laser-output-power-dbm", 0.0)
            rx_signal_power = get_value(optics, "rx-signal-avg-optical-power", 0.0)
            rx_signal_power_dbm = get_value(optics, "rx-signal-avg-optical-power-dbm", 0.0)
            module_temperature = get_value(optics, "module-temperature", 0.0)

            # Temperature might have celsius attribute
            temp_items = optics.get("module-temperature", [{}])
            if temp_items and isinstance(temp_items, list) and len(temp_items) > 0:
                attrs = temp_items[0].get("attributes", {})
                if "junos:celsius" in attrs:
                    module_temperature = float(attrs["junos:celsius"])

            laser_bias_current = get_value(optics, "laser-bias-current", 0.0)
            module_voltage = get_value(optics, "module-voltage", 0.0)

            # Extract alarm states
            tx_power_high_alarm = get_alarm_state(optics, "laser-tx-power-high-alarm")
            tx_power_low_alarm = get_alarm_state(optics, "laser-tx-power-low-alarm")
            tx_power_high_warn = get_alarm_state(optics, "laser-tx-power-high-warn")
            tx_power_low_warn = get_alarm_state(optics, "laser-tx-power-low-warn")

            rx_power_high_alarm = get_alarm_state(optics, "laser-rx-power-high-alarm")
            rx_power_low_alarm = get_alarm_state(optics, "laser-rx-power-low-alarm")
            rx_power_high_warn = get_alarm_state(optics, "laser-rx-power-high-warn")
            rx_power_low_warn = get_alarm_state(optics, "laser-rx-power-low-warn")

            temp_high_alarm = get_alarm_state(optics, "module-temperature-high-alarm")
            temp_low_alarm = get_alarm_state(optics, "module-temperature-low-alarm")
            temp_high_warn = get_alarm_state(optics, "module-temperature-high-warn")
            temp_low_warn = get_alarm_state(optics, "module-temperature-low-warn")

            bias_high_alarm = get_alarm_state(optics, "laser-bias-current-high-alarm")
            bias_low_alarm = get_alarm_state(optics, "laser-bias-current-low-alarm")
            bias_high_warn = get_alarm_state(optics, "laser-bias-current-high-warn")
            bias_low_warn = get_alarm_state(optics, "laser-bias-current-low-warn")

            # Extract alarm thresholds
            tx_power_high_alarm_threshold = get_value(
                optics, "laser-tx-power-high-alarm-threshold-dbm"
            )
            tx_power_low_alarm_threshold = get_value(
                optics, "laser-tx-power-low-alarm-threshold-dbm"
            )
            tx_power_high_warn_threshold = get_value(
                optics, "laser-tx-power-high-warn-threshold-dbm"
            )
            tx_power_low_warn_threshold = get_value(
                optics, "laser-tx-power-low-warn-threshold-dbm"
            )

            rx_power_high_alarm_threshold = get_value(
                optics, "laser-rx-power-high-alarm-threshold-dbm"
            )
            rx_power_low_alarm_threshold = get_value(
                optics, "laser-rx-power-low-alarm-threshold-dbm"
            )
            rx_power_high_warn_threshold = get_value(
                optics, "laser-rx-power-high-warn-threshold-dbm"
            )
            rx_power_low_warn_threshold = get_value(
                optics, "laser-rx-power-low-warn-threshold-dbm"
            )

            temp_high_alarm_threshold = get_value(
                optics, "module-temperature-high-alarm-threshold"
            )
            temp_low_alarm_threshold = get_value(
                optics, "module-temperature-low-alarm-threshold"
            )
            temp_high_warn_threshold = get_value(
                optics, "module-temperature-high-warn-threshold"
            )
            temp_low_warn_threshold = get_value(
                optics, "module-temperature-low-warn-threshold"
            )

            bias_high_alarm_threshold = get_value(
                optics, "laser-bias-current-high-alarm-threshold"
            )
            bias_low_alarm_threshold = get_value(
                optics, "laser-bias-current-low-alarm-threshold"
            )
            bias_high_warn_threshold = get_value(
                optics, "laser-bias-current-high-warn-threshold"
            )
            bias_low_warn_threshold = get_value(
                optics, "laser-bias-current-low-warn-threshold"
            )

            return OpticalDiagnostics(
                interface_name=interface,
                laser_output_power=laser_output_power,
                laser_output_power_dbm=laser_output_power_dbm,
                rx_signal_power=rx_signal_power,
                rx_signal_power_dbm=rx_signal_power_dbm,
                module_temperature=module_temperature,
                laser_bias_current=laser_bias_current,
                module_voltage=module_voltage,
                tx_power_high_alarm=tx_power_high_alarm,
                tx_power_low_alarm=tx_power_low_alarm,
                tx_power_high_warn=tx_power_high_warn,
                tx_power_low_warn=tx_power_low_warn,
                rx_power_high_alarm=rx_power_high_alarm,
                rx_power_low_alarm=rx_power_low_alarm,
                rx_power_high_warn=rx_power_high_warn,
                rx_power_low_warn=rx_power_low_warn,
                temp_high_alarm=temp_high_alarm,
                temp_low_alarm=temp_low_alarm,
                temp_high_warn=temp_high_warn,
                temp_low_warn=temp_low_warn,
                bias_high_alarm=bias_high_alarm,
                bias_low_alarm=bias_low_alarm,
                bias_high_warn=bias_high_warn,
                bias_low_warn=bias_low_warn,
                tx_power_high_alarm_threshold=tx_power_high_alarm_threshold,
                tx_power_low_alarm_threshold=tx_power_low_alarm_threshold,
                tx_power_high_warn_threshold=tx_power_high_warn_threshold,
                tx_power_low_warn_threshold=tx_power_low_warn_threshold,
                rx_power_high_alarm_threshold=rx_power_high_alarm_threshold,
                rx_power_low_alarm_threshold=rx_power_low_alarm_threshold,
                rx_power_high_warn_threshold=rx_power_high_warn_threshold,
                rx_power_low_warn_threshold=rx_power_low_warn_threshold,
                temp_high_alarm_threshold=temp_high_alarm_threshold,
                temp_low_alarm_threshold=temp_low_alarm_threshold,
                temp_high_warn_threshold=temp_high_warn_threshold,
                temp_low_warn_threshold=temp_low_warn_threshold,
                bias_high_alarm_threshold=bias_high_alarm_threshold,
                bias_low_alarm_threshold=bias_low_alarm_threshold,
                bias_high_warn_threshold=bias_high_warn_threshold,
                bias_low_warn_threshold=bias_low_warn_threshold,
            )

        except Exception as e:
            logger.error(
                "optical_diagnostics_parse_failed",
                interface=interface,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_interface_statistics(
        self, device_name: str, interface: str
    ) -> Optional[InterfaceStatistics]:
        """
        Fetch extensive interface statistics.

        Args:
            device_name: Name of the device
            interface: Interface name (e.g., "ge-0/0/6")

        Returns:
            InterfaceStatistics object or None if not available
        """
        device_session = self.conn_mgr.sessions.get(device_name)
        if not device_session:
            logger.warning(
                "interface_stats_device_not_found",
                device=device_name,
                interface=interface,
            )
            return None

        try:
            # Run the command via PyEZ CLI (not RPC - use cli() for | display json commands)
            cmd = f"show interfaces {interface} extensive | display json"
            result = await device_session.cli(cmd)

            if not result:
                logger.debug(
                    "interface_stats_no_result",
                    device=device_name,
                    interface=interface,
                )
                return None

            # Parse the JSON response
            return self._parse_interface_statistics(result, interface)

        except Exception as e:
            logger.error(
                "interface_stats_fetch_failed",
                device=device_name,
                interface=interface,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_chassis_hardware(self, device_name: str) -> Optional[Dict]:
        """
        Fetch chassis hardware information to identify interfaces with LR SFPs.

        Args:
            device_name: Name of the device

        Returns:
            Dictionary with hardware info or None if not available
        """
        device_session = self.conn_mgr.sessions.get(device_name)
        if not device_session:
            logger.warning(
                "chassis_hardware_device_not_found",
                device=device_name,
            )
            return None

        try:
            cmd = "show chassis hardware | display json"
            logger.info("chassis_hardware_fetching", device=device_name, command=cmd)

            result = await device_session.cli(cmd)

            if not result:
                logger.debug("chassis_hardware_no_result", device=device_name)
                return None

            logger.info("chassis_hardware_success", device=device_name)
            return result

        except Exception as e:
            logger.error(
                "chassis_hardware_fetch_failed",
                device=device_name,
                error=str(e),
                exc_info=True,
            )
            return None

    def get_lr_interfaces(self, chassis_hardware: Dict, device_name: str = "") -> Dict[str, Dict]:
        """
        Parse chassis hardware to find interfaces with LR SFPs (10G-LR, 100G-LR).

        Returns dict mapping interface names to their SFP info.

        Example:
            {
                "ge-0/0/6": {
                    "description": "SFP+-10G-LR",
                    "serial_number": "HAG2019341",
                    "part_number": "740-031981"
                },
                "ge-0/0/7": {
                    "description": "SFP+-10G-LR",
                    "serial_number": "HAG2019297",
                    "part_number": "740-031981"
                }
            }
        """
        lr_interfaces = {}

        try:
            chassis_inventory = chassis_hardware.get("chassis-inventory", [{}])[0]
            chassis = chassis_inventory.get("chassis", [{}])[0]
            modules = chassis.get("chassis-module", [])

            logger.info("lr_interfaces_parsing_start", device=device_name)

            for module in modules:
                # Look for FPC modules
                module_name_data = module.get("name", [{}])[0].get("data", "")
                if "FPC" in module_name_data:
                    logger.debug("lr_interfaces_found_fpc", fpc_module=module_name_data)
                    sub_modules = module.get("chassis-sub-module", [])
                    for sub_module in sub_modules:
                        # Look for PIC modules
                        pic_name_data = sub_module.get("name", [{}])[0].get("data", "")
                        if "PIC" in pic_name_data:
                            logger.debug("lr_interfaces_found_pic", pic_module=pic_name_data)
                            sub_sub_modules = sub_module.get("chassis-sub-sub-module", [])
                            for xcvr in sub_sub_modules:
                                # Look for transceivers (Xcvr)
                                xcvr_name_data = xcvr.get("name", [{}])[0].get("data", "")
                                description = xcvr.get("description", [{}])[0].get("data", "")

                                logger.debug(
                                    "lr_interfaces_checking_xcvr",
                                    xcvr=xcvr_name_data,
                                    description=description
                                )

                                # Check if it's an LR module (10G-LR, 100G-LR, etc.)
                                if description and "LR" in description.upper():
                                    # Extract the Xcvr number (e.g., "Xcvr 6" -> 6)
                                    xcvr_number = None
                                    if "Xcvr" in xcvr_name_data:
                                        try:
                                            xcvr_number = int(xcvr_name_data.split()[1])
                                        except (IndexError, ValueError):
                                            logger.warning(
                                                "lr_interfaces_cannot_parse_xcvr_number",
                                                xcvr_name=xcvr_name_data
                                            )
                                            continue

                                    if xcvr_number is not None:
                                        # Map Xcvr number directly to interface
                                        # Xcvr 6 -> ge-0/0/6, Xcvr 7 -> ge-0/0/7
                                        interface_name = f"ge-0/0/{xcvr_number}"

                                        lr_interfaces[interface_name] = {
                                            "description": description,
                                            "serial_number": xcvr.get("serial-number", [{}])[0].get("data", ""),
                                            "part_number": xcvr.get("part-number", [{}])[0].get("data", ""),
                                            "version": xcvr.get("version", [{}])[0].get("data", ""),
                                        }

                                        logger.info(
                                            "lr_interfaces_found",
                                            device=device_name,
                                            interface=interface_name,
                                            description=description,
                                            serial=lr_interfaces[interface_name]["serial_number"]
                                        )

            logger.info(
                "lr_interfaces_found_summary",
                device=device_name,
                count=len(lr_interfaces),
                interfaces=list(lr_interfaces.keys())
            )

            return lr_interfaces

        except Exception as e:
            logger.error(
                "lr_interfaces_parse_failed",
                device=device_name,
                error=str(e),
                exc_info=True,
            )
            return {}

    def _parse_interface_statistics(
        self, rpc_result: Dict, interface: str
    ) -> Optional[InterfaceStatistics]:
        """
        Parse JSON-RPC response for interface statistics.

        Args:
            rpc_result: Raw RPC result from PyEZ
            interface: Interface name

        Returns:
            InterfaceStatistics object or None if parsing fails
        """
        try:
            # Navigate the JSON structure
            interface_info = rpc_result.get("interface-information", [{}])[0]
            physical_interface = interface_info.get("physical-interface", [{}])[0]

            if not physical_interface:
                logger.debug("interface_stats_not_available", interface=interface)
                return None

            # Helper function to extract data field
            def get_value(parent: Dict, key: str, default=None):
                items = parent.get(key, [{}])
                if items and isinstance(items, list) and len(items) > 0:
                    data = items[0].get("data", default)
                    if isinstance(data, str):
                        # Try to convert to int
                        try:
                            return int(data)
                        except ValueError:
                            return default
                    return data
                return default

            # Extract basic interface info
            name = get_value(physical_interface, "name", interface)
            admin_status = get_value(physical_interface, "admin-status", "unknown")
            oper_status = get_value(physical_interface, "oper-status", "unknown")
            description = get_value(physical_interface, "description", "")
            speed = get_value(physical_interface, "speed", "")
            mtu = get_value(physical_interface, "mtu", 1514)
            mac_address = get_value(physical_interface, "current-physical-address", "")
            interface_flapped = get_value(physical_interface, "interface-flapped", "")

            # Extract traffic statistics
            traffic_stats = physical_interface.get("traffic-statistics", [{}])[0]
            input_bytes = get_value(traffic_stats, "input-bytes", 0)
            output_bytes = get_value(traffic_stats, "output-bytes", 0)
            input_packets = get_value(traffic_stats, "input-packets", 0)
            output_packets = get_value(traffic_stats, "output-packets", 0)

            # Extract input errors
            input_errors_list = physical_interface.get("input-error-list", [{}])[0]
            input_errors = get_value(input_errors_list, "input-errors", 0)
            input_drops = get_value(input_errors_list, "input-drops", 0)

            # Extract output errors
            output_errors_list = physical_interface.get("output-error-list", [{}])[0]
            output_errors = get_value(output_errors_list, "output-errors", 0)
            output_drops = get_value(output_errors_list, "output-drops", 0)
            carrier_transitions = get_value(output_errors_list, "carrier-transitions", 0)

            # Extract MAC statistics for CRC errors
            mac_stats = physical_interface.get("ethernet-mac-statistics", [{}])[0]
            input_crc_errors = get_value(mac_stats, "input-crc-errors", 0)
            output_crc_errors = get_value(mac_stats, "output-crc-errors", 0)

            return InterfaceStatistics(
                interface_name=name,
                admin_status=admin_status,
                oper_status=oper_status,
                description=description,
                speed=speed,
                mtu=mtu,
                mac_address=mac_address,
                input_bytes=input_bytes,
                output_bytes=output_bytes,
                input_packets=input_packets,
                output_packets=output_packets,
                input_errors=input_errors,
                output_errors=output_errors,
                input_drops=input_drops,
                output_drops=output_drops,
                input_crc_errors=input_crc_errors,
                output_crc_errors=output_crc_errors,
                carrier_transitions=carrier_transitions,
                interface_flapped=interface_flapped,
            )

        except Exception as e:
            logger.error(
                "interface_stats_parse_failed",
                interface=interface,
                error=str(e),
                exc_info=True,
            )
            return None

    async def get_interface_full_data(
        self, device_name: str, interface: str
    ) -> Dict[str, Any]:
        """
        Fetch both optical diagnostics and interface statistics for an interface.

        Args:
            device_name: Name of the device
            interface: Interface name (e.g., "ge-0/0/6")

        Returns:
            Dictionary with both optical diagnostics and interface statistics
        """
        optical = await self.get_optical_diagnostics(device_name, interface)
        stats = await self.get_interface_statistics(device_name, interface)

        return {
            "device": device_name,
            "interface": interface,
            "optical_diagnostics": optical.to_dict() if optical else None,
            "interface_stats": stats.to_dict() if stats else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
