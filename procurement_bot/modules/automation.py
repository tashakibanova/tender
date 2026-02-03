"""Screen automation wrapper for PyAutoGUI."""

from __future__ import annotations

from typing import Tuple

from utils.gui_automation import click_at, type_text


class ScreenAutomation:
    def fill_field(self, position: Tuple[int, int], text: str) -> None:
        click_at(position)
        type_text(text)
