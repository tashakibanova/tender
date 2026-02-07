"""SearchKeywordsManager: редактор search_keywords.json в интерфейсе Tkinter."""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk


class SearchKeywordsManager:
    """Управляет ключевыми словами поиска внутри приложения."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ORGANIZATIONS_DIR = os.path.join(BASE_DIR, "organizations")
    FILE_NAME = "search_keywords.json"

    @classmethod
    def load_keywords(cls, inn: str) -> list[str]:
        """Возвращает список ключевых слов для выбранной организации."""
        path = cls._keywords_path(inn)
        if not os.path.exists(path):
            cls.save_keywords(inn, [])
            return []
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return [str(item) for item in data]
        return [str(item) for item in data.get("keywords", [])]

    @classmethod
    def save_keywords(cls, inn: str, keywords: list[str]) -> None:
        """Сохраняет ключевые слова для выбранной организации."""
        os.makedirs(cls._org_dir(inn), exist_ok=True)
        path = cls._keywords_path(inn)
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"keywords": keywords}, file, ensure_ascii=False, indent=2)

    @classmethod
    def open_keywords_editor(cls, inn: str) -> None:
        """Открывает окно редактирования ключевых слов."""
        window = tk.Toplevel()
        window.title("Ключевые слова поиска")
        window.geometry("420x360")

        keywords = cls.load_keywords(inn)
        listbox = tk.Listbox(window, height=10)
        for item in keywords:
            listbox.insert("end", item)
        listbox.pack(fill="both", expand=True, padx=12, pady=8)

        entry_frame = tk.Frame(window)
        entry_frame.pack(fill="x", padx=12, pady=4)
        keyword_var = tk.StringVar()
        tk.Entry(entry_frame, textvariable=keyword_var).pack(side="left", fill="x", expand=True)

        def add_keyword() -> None:
            value = keyword_var.get().strip()
            if value:
                listbox.insert("end", value)
                keyword_var.set("")

        tk.Button(entry_frame, text="Добавить", command=add_keyword).pack(side="left", padx=6)

        def remove_selected() -> None:
            selection = listbox.curselection()
            for index in reversed(selection):
                listbox.delete(index)

        tk.Button(window, text="Удалить выбранное", command=remove_selected).pack(pady=4)

        def save_keywords() -> None:
            updated = list(listbox.get(0, "end"))
            cls.save_keywords(inn, updated)
            window.destroy()

        ttk.Button(window, text="Сохранить", command=save_keywords).pack(pady=8)

    @classmethod
    def _org_dir(cls, inn: str) -> str:
        return os.path.join(cls.ORGANIZATIONS_DIR, inn)

    @classmethod
    def _keywords_path(cls, inn: str) -> str:
        return os.path.join(cls._org_dir(inn), cls.FILE_NAME)
