import pytest
from unittest.mock import MagicMock, patch
from jnpr.junos import Device

@pytest.fixture
def mock_device():
    with patch("backend.core.connection_engine.Device") as mock:
        dev = mock.return_value
        dev.open.return_value = True
        dev.connected = True
        yield dev

@pytest.fixture
def mock_config():
    class MockThresholds:
        optical_power = {"warn": -12.0, "critical": -17.0}
        error_ratio = {"warn": 0.0005, "critical": 0.001}
        alert_cooldown = 300

        def get(self, key, default=None):
            return getattr(self, key, default)

    class MockConfig:
        thresholds = MockThresholds()
        sites = {"site_a": ["router1", "router2"]}
        polling_interval = 60
        retry_attempts = 3
        cache_ttl = 300

    return MockConfig()
