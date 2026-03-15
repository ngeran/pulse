"""
activity_log.py
───────────────
Reusable realtime activity log widget for displaying server messages.

Subscribes to backend events and displays them with timestamps and
color-coded severity levels. Can be used across multiple screens.
"""

from typing import Optional, List
from datetime import datetime
from textual.widgets import Static
from textual.containers import Vertical
from textual.reactive import reactive
from textual.app import ComposeResult
from frontend.ui.mixins.event_subscriber import EventSubscriberMixin


class ActivityLog(Vertical, EventSubscriberMixin):
    """
    Realtime activity log with timestamps and color-coded entries.

    Features:
    - Timestamps on all entries (HH:MM:SS format)
    - Single-line format for space efficiency
    - Color-coded by severity (info, success, warning, error)
    - Scrollable to see all messages
    - Configurable max entries
    - Optional WebSocket event subscription
    - Auto-unsubscribe on unmount (via EventSubscriberMixin)

    Example usage:
        yield ActivityLog(id="activity-log")

        # Add log entry
        log = query_one("#activity-log", ActivityLog)
        log.add_entry("Connected to device", "success")
    """

    # Log severity icons
    LOG_ICONS = {
        "info": "→",
        "success": "✓",
        "warning": "⚠",
        "error": "✖",
    }

    # Log colors (OLED-friendly dim colors)
    LOG_COLORS = {
        "info": "#6a8a8a",      # Dim teal/cyan
        "success": "#5aba5a",   # Dim green
        "warning": "#ba8a5a",   # Dim orange/amber
        "error": "#ba5a5a",     # Dim red
    }

    def __init__(
        self,
        max_entries: int = 100,
        show_timestamps: bool = True,
        auto_subscribe: bool = True,
        **kwargs
    ):
        """
        Initialize the activity log.

        Args:
            max_entries: Maximum number of entries to keep (default: 100)
            show_timestamps: Show timestamps on entries (default: True)
            auto_subscribe: Automatically subscribe to backend events (default: True)
        """
        super().__init__(**kwargs)
        self._max_entries = max_entries
        self._show_timestamps = show_timestamps
        self._auto_subscribe = auto_subscribe
        self._entries: List[tuple] = []  # (timestamp, message, severity)
        self._static_widget: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Compose the activity log with a scrollable static widget."""
        yield Static(id="activity-log-content")

    def _get_static(self) -> Static:
        """Get the inner static widget."""
        if not self._static_widget:
            try:
                self._static_widget = self.query_one("#activity-log-content", Static)
            except Exception:
                # Widget not composed yet, return None
                return None
        return self._static_widget

    def on_unmount(self) -> None:
        """Clean up when unmounted."""
        super().on_unmount()
        self._static_widget = None

    async def on_mount(self) -> None:
        """Initialize the log and optionally subscribe to events."""
        # Don't update display yet - wait for compose to complete
        # Subscribe to backend events if requested
        if self._auto_subscribe:
            await self._subscribe_to_events()

    async def _subscribe_to_events(self) -> None:
        """Subscribe to backend connection events."""
        try:
            app = self.app
            if hasattr(app, 'conn_mgr') and app.conn_mgr:
                # Subscribe to connection events and store subscription ID
                self._event_subscription_id = await app.conn_mgr.subscribe_to_events(
                    self._handle_backend_event
                )
        except Exception as e:
            # Silently fail - log will still work without event subscription
            pass

    def _handle_backend_event(self, event) -> None:
        """
        Handle backend events and add them to the log.

        Args:
            event: EventMessage from backend
        """
        try:
            from backend.core.events import EventMessage, ConnectionEvent, HealthEvent

            if not isinstance(event, EventMessage):
                return

            # Map event types to log severity
            severity = "info"
            message = ""

            if event.event_type == ConnectionEvent.CONNECTED:
                severity = "success"
                # Check if this is a device or WebSocket connection
                if event.device_name == "WebSocket":
                    msg = event.data.get("message", "WebSocket connected") if event.data else "WebSocket connected"
                    message = f"✓ {msg}"
                else:
                    message = f"✓ Connected: {event.device_name}"
            elif event.event_type == ConnectionEvent.DISCONNECTED:
                severity = "warning"
                message = f"⚠ Disconnected: {event.device_name}"
            elif event.event_type == ConnectionEvent.PROGRESS:
                severity = "info"
                # Progress events have message in data
                progress_msg = event.data.get("message", "") if event.data else ""
                message = f"→ {event.device_name}: {progress_msg}" if progress_msg else f"→ {event.device_name}: Progress"
            elif event.event_type == ConnectionEvent.ERROR:
                severity = "error"
                # Error events have message or attempt info in data
                if event.data and "message" in event.data:
                    message = f"✖ {event.device_name}: {event.data['message']}"
                else:
                    attempt = event.data.get("attempt", "?") if event.data else "?"
                    message = f"✖ {event.device_name}: Connection attempt {attempt} failed"
            elif event.event_type == ConnectionEvent.STATE_CHANGED:
                state = event.data.get("state", "") if event.data else ""
                if state == "FAILED":
                    severity = "error"
                    message = f"✖ Connection failed: {event.device_name} (all retries exhausted)"
                else:
                    severity = "info"
                    message = f"→ {event.device_name}: State changed to {state}"
            elif event.event_type == HealthEvent.CIRCUIT_SICK:
                severity = "warning"
                message = f"⚠ Health degraded: {event.device_name}"
            elif event.event_type == HealthEvent.CIRCUIT_DEAD:
                severity = "error"
                message = f"✖ Circuit critical: {event.device_name}"
            elif event.event_type == HealthEvent.SPOF_DETECTED:
                severity = "error"
                message = f"⚠ SPOF detected: {event.device_name}"
            else:
                # Default for unknown event types
                severity = "info"
                message = f"→ {event.device_name}: {event.event_type.value}"

            # Add entry from event
            self.add_entry(message, severity)

        except Exception as e:
            # If event parsing fails, add a generic message instead of raw str(event)
            import traceback
            traceback.print_exc()  # For debugging
            device = getattr(event, 'device_name', 'Unknown')
            self.add_entry(f"→ {device}: Event logged (see logs for details)", "info")

    def add_entry(self, message: str, severity: str = "info", timestamp: Optional[str] = None) -> None:
        """
        Add a log entry.

        Args:
            message: Log message
            severity: Entry severity (info, success, warning, error)
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")

        # Normalize severity
        severity = severity.lower()
        if severity not in self.LOG_ICONS:
            severity = "info"

        self._entries.append((timestamp, message, severity))

        # Trim old entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        self._update_display()

    def _update_display(self) -> None:
        """Update the log display with all entries."""
        static = self._get_static()

        if not static:
            return

        if not self._entries:
            static.update("[dim]No activity yet[/]")
            return

        lines = []
        for timestamp, message, severity in self._entries:
            icon = self.LOG_ICONS.get(severity, "→")
            color = self.LOG_COLORS.get(severity, "#ffffff")

            if self._show_timestamps:
                lines.append(
                    f"[dim]{timestamp}[/] [{color}]{icon}[/{color}] {message}"
                )
            else:
                lines.append(
                    f"[{color}]{icon}[/{color}] {message}"
                )

        static.update("\n".join(lines))

    def clear(self) -> None:
        """Clear all log entries."""
        self._entries = []
        self._update_display()

    def write_line(self, line: str) -> None:
        """
        Add a plain line to the log (compatibility with Log widget).

        Args:
            line: Text line to add
        """
        # Try to detect severity from common prefixes
        severity = "info"
        if line.startswith("[ERROR]") or line.startswith("ERROR:"):
            severity = "error"
            line = line.replace("[ERROR]", "").replace("ERROR:", "").strip()
        elif line.startswith("[WARNING]") or line.startswith("WARN:"):
            severity = "warning"
            line = line.replace("[WARNING]", "").replace("WARN:", "").strip()
        elif line.startswith("[SUCCESS]") or line.startswith("✓"):
            severity = "success"
            line = line.replace("[SUCCESS]", "").replace("✓", "").strip()
        elif line.startswith("[INFO]"):
            line = line.replace("[INFO]", "").strip()

        self.add_entry(line, severity)

        # Scroll to bottom to show latest message
        try:
            static = self._get_static()
            static.scroll_end(animate=False)
        except Exception:
            pass  # Scroll failed, not critical
