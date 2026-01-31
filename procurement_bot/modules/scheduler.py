"""Simple scheduler for periodic monitoring."""

from __future__ import annotations

from typing import Callable


class MonitoringScheduler:
    def __init__(self, interval_minutes: int, callback: Callable[[], None]) -> None:
        self.interval_seconds = interval_minutes * 60
        self.callback = callback
        self._running = False
        self._after_id: str | None = None

    def start_tk(self, widget) -> None:
        if self._running:
            return
        self._running = True
        self._schedule_next(widget)

    def stop(self) -> None:
        self._running = False
        if self._after_id and hasattr(self, "_tk_widget"):
            self._tk_widget.after_cancel(self._after_id)
            self._after_id = None

    def _schedule_next(self, widget) -> None:
        self._tk_widget = widget
        if not self._running:
            return
        self.callback()
        self._after_id = widget.after(self.interval_seconds * 1000, self._schedule_next, widget)
