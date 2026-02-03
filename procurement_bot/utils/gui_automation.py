"""GUI automation via PyAutoGUI."""

from __future__ import annotations

from typing import Tuple

import pyautogui


def click_at(position: Tuple[int, int]) -> None:
    pyautogui.click(position[0], position[1])


def type_text(text: str) -> None:
    pyautogui.write(text, interval=0.02)
