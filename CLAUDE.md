# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pulse is a terminal-based circuit health monitoring application for Juniper networks. It combines a Textual terminal UI with a FastAPI WebSocket backend to provide real-time monitoring of network device interfaces, optical power levels, error ratios, and health scoring.

## Architecture

The application follows a **decoupled event-driven architecture** with three main layers:

### Backend Layer (`backend/`)
- **`api/`**: FastAPI WebSocket server on port 8001 that broadcasts events to connected clients
- **`core/`**: Business logic engines
  - `connection_engine.py`: Manages PyEZ device connections using NETCONF/SSH
  - `interface_discovery.py`: Discovers and caches interface information using PyEZ tables
  - `logic_engine.py`: Health scoring engine that calculates GREEN/YELLOW/RED status based on configurable thresholds
  - `events.py`: Event system with `ConnectionEvent` and `HealthEvent` enums, `EventMessage` dataclass
- **`config/`**: Configuration management using YAML
- **`utils/`**: Structlog-based logging with JSON output to `logs/pulse.log`

### Frontend Layer (`frontend/`)
- **`ui/app.py`**: Main `PulseApp` class extending Textual App
- **`ui/screens/`**: Modal screens (e.g., `ConnectionScreen` for adding devices)
- Key widgets: `DeviceTree`, `HealthDashboard`, `EventLog`, `BackendStatus`, `SPOFAlertPanel`

### Event System
The architecture uses a publisher/subscriber pattern:
- Components subscribe to events via `conn_mgr.subscribe_to_events(callback)`
- Events are emitted with `_emit_event(event_type, device_name, data)`
- Both sync and async callbacks are supported
- WebSocket server subscribes to backend events and broadcasts to frontend

## Development Commands

### Running the Application
```bash
./run.sh                # Creates venv, installs deps, and launches the app
python __main__.py      # Direct launch (requires venv activated)
```

### Testing
```bash
pytest                          # Run all tests
pytest tests/test_connection.py # Run specific test file
pytest -v                       # Verbose output
```

Tests are located in `tests/` and use pytest with pytest-asyncio (asyncio_mode: auto).

### Code Quality
```bash
black .                # Format code (line-length: 88)
isort .                # Sort imports (profile: black)
mypy backend/ frontend/ # Type checking (strict mode)
```

## Configuration

Main configuration is in `config.yaml`:
- `polling_interval`: Seconds between health checks (default: 60)
- `connection_timeout`: Seconds before connection timeout (default: 30)
- `retry_attempts`: Number of connection retry attempts (default: 3)
- `cache_ttl`: Interface discovery cache TTL in seconds (default: 300)
- `thresholds`: Optical power and error ratio thresholds for health scoring
- `ui`: Refresh rate, color scheme, log retention

## Key Technical Patterns

### Async/Sync Bridge
PyEZ operations are blocking and must be run in executors:
```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, self.dev.open)
```

### Event Subscription
Components subscribe to events during initialization:
```python
await self.conn_mgr.subscribe_to_events(self.handle_connection_event)
```

### Progress Callbacks
Long-running operations accept progress callbacks for UI feedback:
```python
async def connect(self, progress_callback: Optional[Callable[[str], Any]] = None):
    if progress_callback:
        progress_callback("Opening NETCONF session")
```

## Device Connection

Devices are connected using PyEZ (junos-eznc) via NETCONF over SSH. The `DeviceSession` class wraps PyEZ's `Device` class with async methods and state tracking. Interfaces with prefixes `xe-`, `et-`, and `ge-` are monitored.

## Health Scoring

Health scores are calculated by `HealthScoringEngine` based on:
- Optical power levels (warn: -12dBm, critical: -17dBm)
- Error ratios (warn: 0.0005, critical: 0.001)
- MACsec errors

Status levels: GREEN (healthy), YELLOW (degraded), RED (failed)
