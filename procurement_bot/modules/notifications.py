"""Desktop notification helper."""

from plyer import notification


class DesktopNotifier:
    def notify_new_lots(self, count: int) -> None:
        notification.notify(
            title="Новые лоты",
            message=f"Найдено новых лотов: {count}",
            timeout=10,
        )
