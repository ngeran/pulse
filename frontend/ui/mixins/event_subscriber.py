"""
event_subscriber.py
───────────────────
Mixin for widgets that subscribe to backend events.

Provides automatic subscription management with cleanup on unmount.
"""

from typing import Optional
from textual.app import ComposeResult


class EventSubscriberMixin:
    """
    Mixin for widgets that subscribe to backend events.

    Features:
    - Stores subscription ID
    - Auto-unsubscribes on unmount
    - Provides helper methods for subscription management

    Usage:
        class MyWidget(Static, EventSubscriberMixin):
            async def on_mount(self):
                # Subscribe to events
                self._event_subscription_id = await self.app.conn_mgr.subscribe_to_events(
                    self._handle_event
                )

            def _handle_event(self, event):
                # Handle event
                pass

        # No need to manually unsubscribe - mixin handles it
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the event subscriber.

        Note: When using this mixin, call super().__init__() first
        """
        super().__init__(*args, **kwargs)
        self._event_subscription_id: Optional[str] = None
        self._health_subscription_id: Optional[str] = None

    def on_unmount(self) -> None:
        """
        Auto-unsubscribe from backend events when widget is unmounted.

        This method is called by Textual when the widget is removed from the screen.
        It automatically unsubscribes from any active backend event subscriptions.
        """
        # Unsubscribe from connection events (if attribute exists and has value)
        if hasattr(self, '_event_subscription_id') and self._event_subscription_id and hasattr(self.app, 'conn_mgr'):
            try:
                # Create async task for unsubscribe
                import asyncio
                asyncio.create_task(
                    self.app.conn_mgr.unsubscribe_from_events(self._event_subscription_id)
                )
                self._event_subscription_id = None
            except Exception as e:
                # Log but don't raise - unmount should complete
                from backend.utils.logging import logger
                logger.warning("event_unsubscribe_error", widget=self.id, error=str(e))

        # Unsubscribe from health events (if attribute exists and has value)
        if hasattr(self, '_health_subscription_id') and self._health_subscription_id and hasattr(self.app, 'health_engine'):
            try:
                import asyncio
                asyncio.create_task(
                    self.app.health_engine.unsubscribe_from_events(self._health_subscription_id)
                )
                self._health_subscription_id = None
            except Exception as e:
                from backend.utils.logging import logger
                logger.warning("health_unsubscribe_error", widget=self.id, error=str(e))

        # Call parent's on_unmount if it exists
        if hasattr(super(), 'on_unmount'):
            super().on_unmount()

    async def unsubscribe_from_events(self) -> None:
        """
        Manually unsubscribe from all backend events.

        This can be called to explicitly clean up subscriptions before
        the widget is unmounted.
        """
        if self._event_subscription_id:
            await self.app.conn_mgr.unsubscribe_from_events(self._event_subscription_id)
            self._event_subscription_id = None

        if self._health_subscription_id:
            await self.app.health_engine.unsubscribe_from_events(self._health_subscription_id)
            self._health_subscription_id = None
