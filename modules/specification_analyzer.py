"""TenderSpecificationAnalyzer: окно анализа ТЗ (Tkinter GUI)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from tkinter import ttk
import tkinter as tk

from .manual_tender_entry import ManualTenderEntry


class TenderSpecificationAnalyzer:
    """Интерактивный анализ ТЗ в отдельном окне (Tkinter)."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ORGANIZATIONS_DIR = os.path.join(BASE_DIR, "organizations")

    @classmethod
    def open_analysis_window(cls, tender_id: str, inn: str | None = None) -> None:
        """Открывает окно анализа ТЗ."""
        inn = inn or cls._load_active_inn()
        if not inn:
            raise ValueError("Не указан ИНН для анализа ТЗ.")

        tender_data = cls.load_tender_data(tender_id, inn)
        specification_text = cls.extract_specification_text(tender_id, inn)
        criteria_list = cls.parse_specification(specification_text)
        analogs = cls._find_analogs(criteria_list, inn)
        cls._open_window(tender_data, criteria_list, analogs, specification_text, inn, tender_id)

    @classmethod
    def load_tender_data(cls, tender_id: str, inn: str) -> dict:
        """Загружает метаданные закупки."""
        registry_path = os.path.join(cls._lots_dir(inn), "registry.json")
        if not os.path.exists(registry_path):
            return {}
        with open(registry_path, "r", encoding="utf-8") as file:
            records = json.load(file)
        for record in records:
            if str(record.get("number")) == str(tender_id):
                return record
        return {}

    @classmethod
    def extract_specification_text(cls, tender_id: str, inn: str) -> str:
        """Получает текст ТЗ из ManualTenderEntry."""
        return ManualTenderEntry.get_extracted_text(inn, tender_id)

    @staticmethod
    def parse_specification(text: str) -> list[dict]:
        """Парсит текст ТЗ и возвращает список критериев."""
        criteria = []
        current_section = None
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned.endswith(":") and len(cleaned.split()) <= 4:
                current_section = cleaned.strip(":")
                continue
            if ":" in cleaned:
                key, value = cleaned.split(":", 1)
                criteria.append(
                    {
                        "criterion": key.strip(),
                        "requirement": value.strip(),
                        "section": current_section,
                    }
                )
        return criteria

    @classmethod
    def _find_analogs(cls, criteria_list: list[dict], inn: str) -> list[dict]:
        """Ищет аналоги через модуль каталога (если доступен)."""
        try:
            from .catalog_module import find_analogs  # type: ignore

            return find_analogs(criteria_list, inn)
        except Exception:
            return [{"analog": "", "price": "", "status": "❓"} for _ in criteria_list]

    @classmethod
    def _open_window(
        cls,
        tender_data: dict,
        criteria_list: list[dict],
        analogs: list[dict],
        specification_text: str,
        inn: str,
        tender_id: str,
    ) -> None:
        window = tk.Toplevel()
        window.title("Анализ технического задания")
        window.geometry("1000x700")

        header_frame = tk.Frame(window, padx=8, pady=8)
        header_frame.pack(fill="x")
        cls._render_header(header_frame, tender_data)

        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", expand=True)

        sections = cls._group_by_section(criteria_list)
        for section, items in sections.items():
            tab = tk.Frame(notebook)
            notebook.add(tab, text=section)
            cls._render_table(tab, items, analogs, inn, tender_id)

        if cls._needs_commercial_offer(specification_text):
            offer_tab = tk.Frame(notebook)
            notebook.add(offer_tab, text="Коммерческое предложение")
            text_widget = tk.Text(offer_tab, height=10)
            text_widget.pack(fill="both", expand=True)

        window.protocol(
            "WM_DELETE_WINDOW",
            lambda: cls._on_close(window, inn, tender_id),
        )

    @staticmethod
    def _render_header(frame: tk.Frame, data: dict) -> None:
        labels = [
            ("Номер/URL", data.get("url") or data.get("number", "")),
            ("Наименование", data.get("title", "")),
            ("Заказчик", data.get("customer", "")),
            ("Дата окончания", data.get("deadline", "")),
            ("НМЦК", data.get("price", "")),
            ("Регион", data.get("region", "")),
            ("Тип", data.get("type", "")),
            ("Статус", data.get("status", "")),
        ]
        for idx, (label, value) in enumerate(labels):
            tk.Label(frame, text=f"{label}: {value}", anchor="w").grid(
                row=idx // 2, column=idx % 2, sticky="w", padx=4, pady=2
            )

    @classmethod
    def _render_table(
        cls,
        parent: tk.Frame,
        criteria_list: list[dict],
        analogs: list[dict],
        inn: str,
        tender_id: str,
    ) -> None:
        columns = ("criterion", "requirement", "analog", "price", "status")
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        tree.heading("criterion", text="Критерий")
        tree.heading("requirement", text="Требование заказчика")
        tree.heading("analog", text="Аналог из каталога")
        tree.heading("price", text="Цена")
        tree.heading("status", text="Статус")
        tree.pack(fill="both", expand=True)

        for idx, item in enumerate(criteria_list):
            analog = analogs[idx] if idx < len(analogs) else {"analog": "", "price": "", "status": "❓"}
            tree.insert(
                "",
                "end",
                values=(
                    item.get("criterion", ""),
                    item.get("requirement", ""),
                    analog.get("analog", ""),
                    analog.get("price", ""),
                    analog.get("status", "❓"),
                ),
            )

        tree.bind("<Double-1>", lambda event: cls._edit_cell(tree, event, inn, tender_id))

    @staticmethod
    def _edit_cell(tree: ttk.Treeview, event, inn: str, tender_id: str) -> None:
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        column = tree.identify_column(event.x)
        if column != "#3":
            return
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        x, y, width, height = tree.bbox(row_id, column)
        value = tree.set(row_id, "analog")
        entry = tk.Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)

        def save_edit(_event=None):
            tree.set(row_id, "analog", entry.get())
            tree.set(row_id, "status", "✅" if entry.get() else "⚠️")
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    @classmethod
    def _group_by_section(cls, criteria_list: list[dict]) -> dict:
        grouped: dict[str, list[dict]] = {}
        for item in criteria_list:
            section = item.get("section") or "Общее"
            grouped.setdefault(section, []).append(item)
        return grouped

    @staticmethod
    def _needs_commercial_offer(text: str) -> bool:
        keywords = ["коммерческое предложение", "кп", "предоставить коммерческое"]
        lowered = text.lower()
        return any(keyword in lowered for keyword in keywords)

    @classmethod
    def _on_close(cls, window: tk.Toplevel, inn: str, tender_id: str) -> None:
        cls._save_edited_specification(window, inn, tender_id)
        window.destroy()

    @classmethod
    def _save_edited_specification(cls, window: tk.Toplevel, inn: str, tender_id: str) -> None:
        edited = []
        for widget in window.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for tab_id in widget.tabs():
                    tab = widget.nametowidget(tab_id)
                    for child in tab.winfo_children():
                        if isinstance(child, ttk.Treeview):
                            for row in child.get_children():
                                values = child.item(row, "values")
                                edited.append(
                                    {
                                        "criterion": values[0],
                                        "requirement": values[1],
                                        "analog": values[2],
                                        "price": values[3],
                                        "status": values[4],
                                    }
                                )
        path = os.path.join(
            cls._tender_dir(inn, tender_id), "specification_edited.json"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(edited, file, ensure_ascii=False, indent=2)

    @classmethod
    def _tender_dir(cls, inn: str, tender_id: str) -> str:
        return os.path.join(cls._lots_dir(inn), str(tender_id))

    @classmethod
    def _lots_dir(cls, inn: str) -> str:
        return os.path.join(cls.ORGANIZATIONS_DIR, inn, "lots")

    @classmethod
    def _load_active_inn(cls) -> str:
        state_path = os.path.join(cls.BASE_DIR, "launcher_state.json")
        if not os.path.exists(state_path):
            return ""
        with open(state_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("active_inn", "")
