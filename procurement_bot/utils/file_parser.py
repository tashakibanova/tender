"""File parsing helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return pdf_extract_text(file_path)
    if path.suffix.lower() == ".docx":
        document = Document(file_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8")
    raise ValueError("Неподдерживаемый формат файла")


def open_file_for_edit(file_path: str) -> None:
    if sys.platform.startswith("win"):
        subprocess.run(["start", file_path], shell=True, check=False)
        return
    if sys.platform == "darwin":
        subprocess.run(["open", file_path], check=False)
        return
    subprocess.run(["xdg-open", file_path], check=False)
