# Health Dashboard - User Guide

## Overview

The Circuit Health Dashboard provides a comprehensive, real-time view of all circuit health metrics in a modular grid layout.

## Access

Press **`h`** in the main app to open the Health Dashboard.

## Layout

The dashboard uses a **2x2 grid layout** with 4 modular panels:

### Panel 1: 📊 Health Scores (Top-Left)
- Health scores grouped by device
- Shows overall score (0-100) for each interface
- Color-coded: ● Green (healthy), ⚡ Yellow (degraded), ✖ Red (critical)
- Trend indicators: ↗ improving, → stable, ↘ degrading

### Panel 2: 💡 Optical Diagnostics (Top-Right)
- TX/RX power levels for all interfaces
- Module temperature and bias current
- Alarm status indicators (⚠ = threshold breached)

### Panel 3: 🔍 Interface Details (Bottom-Left)
- Selected interface's detailed metrics
- Component score breakdown (Optical, Errors, Stability)
- Error counters and carrier transitions
- Trend indicator with description

### Panel 4: 🚨 Alert History (Bottom-Right)
- Timestamped log of health alerts
- Color-coded by severity
- Auto-scrolling, keeps last 100 alerts

## Navigation

| Key | Action |
|-----|--------|
| `h` | Open health dashboard |
| `Esc` | Return to main view |
| `1` | Focus Health Scores panel |
| `2` | Focus Optical Diagnostics panel |
| `3` | Focus Interface Details panel |
| `4` | Focus Alert History panel |
| `Tab` | Cycle through panels |
| `↑` `↓` | Scroll within panel |

## Customizing the Grid

The dashboard is designed to be modular. To add/remove/rearrange panels:

### 1. Panel Classes

Each panel is a separate class in `frontend/ui/screens/health_dashboard.py`:

```python
class HealthScoresPanel(HealthPanel):
    """Panel 1: Health scores"""
    pass

class OpticalDiagnosticsPanel(HealthPanel):
    """Panel 2: Optical diagnostics"""
    pass

class InterfaceDetailsPanel(HealthPanel):
    """Panel 3: Interface details"""
    pass

class AlertHistoryPanel(HealthPanel):
    """Panel 4: Alert history"""
    pass
```

### 2. Grid Layout

The grid is defined in `HealthDashboardScreen.compose()`:

```python
with Container(id="dashboard-grid"):
    with Horizontal():  # Row 1
        yield HealthScoresPanel(id="health-scores")
        yield OpticalDiagnosticsPanel(id="optics-table")

    with Horizontal():  # Row 2
        yield InterfaceDetailsPanel(id="interface-details")
        yield AlertHistoryPanel(id="alert-history")
```

### 3. To Add a New Panel

1. Create a new panel class extending `HealthPanel`:

```python
class MyCustomPanel(HealthPanel):
    def __init__(self, **kwargs):
        super().__init__(title="🔧 My Panel", **kwargs)

    def _compose_content(self) -> ComposeResult:
        with Vertical(id="content", classes="PanelContent"):
            yield Static("My panel content here")
```

2. Add it to the grid:

```python
with Container(id="dashboard-grid"):
    with Horizontal():
        yield HealthScoresPanel(id="health-scores")
        yield OpticalDiagnosticsPanel(id="optics-table")
        yield MyCustomPanel(id="my-panel")  # New panel
```

3. Update grid size in CSS if needed:

```css
DashboardGrid {
    grid-size: 3 2;  /* 3 columns, 2 rows */
}
```

### 4. To Remove a Panel

Simply comment out or remove the panel from the `compose()` method:

```python
with Horizontal():
    yield HealthScoresPanel(id="health-scores")
    # yield OpticalDiagnosticsPanel(id="optics-table")  # Removed
```

### 5. To Reorder Panels

Move panels to different positions in the grid:

```python
with Horizontal():  # Row 1
    yield AlertHistoryPanel(id="alert-history")         # Moved to top-left
    yield InterfaceDetailsPanel(id="interface-details") # Moved to top-right

with Horizontal():  # Row 2
    yield HealthScoresPanel(id="health-scores")         # Moved to bottom-left
    yield OpticalDiagnosticsPanel(id="optics-table")     # Moved to bottom-right
```

## Panel Styling

All panels use pure black theme with thin borders. To customize:

### Panel Border Style

Edit `frontend/styles/dark.tcss`:

```css
HealthPanel {
    border: solid $accent;      /* Change color */
    border-style: double;       /* single, double, thick, etc */
    border-subtitle-align: left;
}
```

### Panel Title

```css
HealthPanel > Static.-panel-title {
    color: $warning;            /* Title color */
    text-style: bold italic;    /* Text style */
    background: $panel;         /* Background color */
}
```

## Data Updates

Panels are updated via method calls:

```python
# Update health scores
scores_panel = screen.query_one("#health-scores", HealthScoresPanel)
scores_panel.update_scores(device_scores_dict)

# Update optical diagnostics
optics_panel = screen.query_one("#optics-table", OpticalDiagnosticsPanel)
optics_panel.table.update_from_diagnostics(diagnostics_dict)

# Update interface details
details_panel = screen.query_one("#interface-details", InterfaceDetailsPanel)
details_panel.update_details(interface_data_dict)

# Add alert
alerts_panel = screen.query_one("#alert-history", AlertHistoryPanel)
alerts_panel.add_alert("Message", severity="WARNING")
```

## Theme Variables

Available color variables in `dark.tcss`:

| Variable | Value | Usage |
|----------|-------|-------|
| `$primary` | Black | Main background |
| `$accent` | Cyan | Active elements, focus |
| `$success` | Green | Healthy states |
| `$warning` | Yellow | Degraded states |
| `$error` | Red | Critical/failure states |
| `$text` | White | Primary text |
| `$text-muted` | Grey66 | Secondary text |
| `$border` | Grey30 | Thin borders |
