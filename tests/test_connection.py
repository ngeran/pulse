import pytest
import asyncio
from backend.core.connection_engine import ConnectionManager, ConnectionState

@pytest.mark.asyncio
async def test_connection_manager_connect(mock_device):
    cm = ConnectionManager(max_sessions=2, retry_limit=1)
    session = await cm.connect_device("router1", "admin", "pass")
    
    assert session.host == "router1"
    assert session.state == ConnectionState.CONNECTED
    await cm.close_all()

@pytest.mark.asyncio
async def test_connection_manager_pool_limit(mock_device):
    cm = ConnectionManager(max_sessions=1, retry_limit=1)
    await cm.connect_device("router1", "admin", "pass")
    
    with pytest.raises(RuntimeError, match="Connection pool full"):
        await cm.connect_device("router2", "admin", "pass")
    await cm.close_all()

@pytest.mark.asyncio
async def test_heartbeat_logic(mock_device):
    cm = ConnectionManager(max_sessions=2)
    session = await cm.connect_device("router1", "admin", "pass")
    
    # Mock device becoming disconnected
    mock_device.connected = False
    
    # Run heartbeat once manually or through interval
    await cm._run_heartbeat(0)
    
    # Heartbeat is async, we may need to wait or check state
    assert session.state == ConnectionState.DISCONNECTED
    await cm.close_all()
