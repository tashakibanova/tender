"""LauncherPanel: стартовая панель для демонстрации модулей платформы.

Запуск: python launcher.py
Требуется только стандартная библиотека Python (Tkinter).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk


APP_TITLE = "LauncherPanel"
STATE_FILE = "launcher_state.json"
CONFIG_FILE = "launcher_config.json"
SEARCH_KEYWORDS_FILE = "search_keywords.json"
ORGANIZATIONS_DIR = "organizations"


class LauncherPanel:
    """Стартовая панель (заглушка) для тестирования первых модулей."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.base_path = Path(__file__).resolve().parent
        self.organizations_path = self.base_path / ORGANIZATIONS_DIR
        self.organizations_path.mkdir(exist_ok=True)

        self.state = self._load_state()
        self.config = self._load_config()

        self.active_inn = self.state.get("active_inn") or ""
        self._setup_window()
        self._build_ui()
        self._load_organizations()
        self._maybe_prompt_first_org()

    def _setup_window(self) -> None:
        self.root.title(self._build_title())
        width, height = self.state.get("window_size", [900, 700])
        self.root.geometry(f"{width}x{height}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.configure(padx=16, pady=16)
        self._build_organization_block()
        self._build_search_block()
        self._build_monitoring_block()
        self._build_manual_block()
        self._build_log_block()
        self._set_actions_enabled(bool(self.active_inn))

    def _build_organization_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Организация", padx=8, pady=8)
        frame.pack(fill="x", pady=6)

        tk.Label(frame, text="Выберите организацию").pack(side="left")
        self.org_var = tk.StringVar(value="Выберите организацию")
        self.org_menu = ttk.Combobox(frame, textvariable=self.org_var, state="readonly", width=30)
        self.org_menu.pack(side="left", padx=8)
        self.org_menu.bind("<<ComboboxSelected>>", self._on_org_selected)

        tk.Button(
            frame,
            text="Добавить организацию",
            command=self._create_organization,
        ).pack(side="right", padx=4)
        self.view_profile_button = tk.Button(
            frame,
            text="Просмотреть профиль",
            command=lambda: self._open_profile_window(readonly=True),
        )
        self.view_profile_button.pack(side="right", padx=4)
        self.edit_profile_button = tk.Button(
            frame,
            text="Изменить реквизиты",
            command=lambda: self._open_profile_window(readonly=False),
        )
        self.edit_profile_button.pack(side="right", padx=4)

    def _build_search_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Параметры поиска", padx=8, pady=8)
        frame.pack(fill="x", pady=6)

        self.search_button = tk.Button(
            frame,
            text="Настроить ключевые слова",
            command=self._open_search_keywords_editor,
        )
        self.search_button.pack(side="left", padx=4)

    def _build_monitoring_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Мониторинг закупок", padx=8, pady=8)
        frame.pack(fill="both", expand=True, pady=6)

        self.monitor_button = tk.Button(
            frame,
            text="Запустить мониторинг",
            command=self._run_monitoring,
        )
        self.monitor_button.pack(
            anchor="w", pady=4
        )

        columns = ("title", "price", "deadline", "platform", "action")
        self.tenders_table = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        self.tenders_table.heading("title", text="Название")
        self.tenders_table.heading("price", text="НМЦК")
        self.tenders_table.heading("deadline", text="Дата окончания")
        self.tenders_table.heading("platform", text="Площадка")
        self.tenders_table.heading("action", text="Действие")
        self.tenders_table.column("title", width=260)
        self.tenders_table.column("price", width=90)
        self.tenders_table.column("deadline", width=120)
        self.tenders_table.column("platform", width=120)
        self.tenders_table.column("action", width=110, anchor="center")
        self.tenders_table.pack(fill="both", expand=True)
        self.tenders_table.bind("<Double-1>", self._on_action_click)

    def _build_manual_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Ручной ввод", padx=8, pady=8)
        frame.pack(fill="x", pady=6)

        self.manual_button = tk.Button(
            frame,
            text="Добавить закупку вручную",
            command=self._manual_entry,
        )
        self.manual_button.pack(side="left", padx=4)

    def _build_log_block(self) -> None:
        self.log_frame = tk.LabelFrame(self.root, text="Журнал событий", padx=8, pady=8)
        if self.config.get("mode", "demo") == "debug":
            self.log_frame.pack(fill="both", pady=6)
            self.log_text = tk.Text(self.log_frame, height=8, state="disabled")
            self.log_text.pack(fill="both", expand=True)
        else:
            self.log_text = None

    def _load_organizations(self) -> None:
        organizations = []
        for entry in sorted(self.organizations_path.iterdir()):
            if entry.is_dir():
                organizations.append(entry.name)
            elif entry.is_file() and entry.suffix == ".json":
                organizations.append(entry.stem)
        if not organizations:
            organizations = ["Выберите организацию"]
        self.org_menu["values"] = organizations
        if self.active_inn and self.active_inn in organizations:
            self.org_var.set(self.active_inn)
        else:
            self.org_var.set(organizations[0])

    def _maybe_prompt_first_org(self) -> None:
        if not any(self.organizations_path.iterdir()):
            if messagebox.askyesno(
                "Организация",
                "Папка организаций пуста. Создать первую организацию?",
            ):
                self._create_organization()

    def _on_org_selected(self, _event=None) -> None:
        selection = self.org_var.get()
        if selection and selection != "Выберите организацию":
            self.active_inn = selection
            self.root.title(self._build_title())
            self._log(f"Загружена организация: {selection}")
            self._set_actions_enabled(True)
        else:
            self.active_inn = ""
            self.root.title(self._build_title())
            self._set_actions_enabled(False)

    def _create_organization(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая организация")
        dialog.geometry("420x200")
        dialog.grab_set()

        tk.Label(dialog, text="ИНН (обязательно)").pack(anchor="w", padx=12, pady=6)
        inn_var = tk.StringVar()
        tk.Entry(dialog, textvariable=inn_var).pack(fill="x", padx=12)

        tk.Label(dialog, text="Наименование").pack(anchor="w", padx=12, pady=6)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var).pack(fill="x", padx=12)

        def submit():
            inn = inn_var.get().strip()
            if not inn:
                messagebox.showwarning("Организация", "ИНН обязателен.")
                return
            self._log("Создание организации...")
            profile_data = {
                "basic_info": {
                    "inn": inn,
                    "name": name_var.get().strip() or "нет",
                }
            }
            created = self._call_module(
                "modules.organization_manager",
                "OrganizationManager",
                "create_profile",
                profile_data,
            )
            if created:
                self.active_inn = inn
                self._load_organizations()
                self._set_actions_enabled(True)
                self.root.title(self._build_title())
            dialog.destroy()

        tk.Button(dialog, text="Создать", command=submit).pack(pady=12)

    def _open_search_keywords_editor(self) -> None:
        if not self._ensure_active_inn():
            return
        self._call_module(
            "modules.search_keywords",
            "SearchKeywordsManager",
            "open_keywords_editor",
            self.active_inn,
        )

    def _run_monitoring(self) -> None:
        if not self._ensure_active_inn():
            return
        self._log(f"Запуск мониторинга для ИНН {self.active_inn}...")
        tenders = self._call_module(
            "modules.tender_monitor",
            "TenderMonitor",
            "find_new_tenders",
            self.active_inn,
            default=[],
        )
        self._render_tenders(tenders)
        self._log(f"Найдено лотов: {len(tenders)}")

    def _render_tenders(self, tenders: list) -> None:
        for item in self.tenders_table.get_children():
            self.tenders_table.delete(item)
        for tender in tenders:
            tender_id = tender.get("id", "")
            title = tender.get("title", "")
            price = tender.get("price", "")
            deadline = tender.get("deadline", "")
            platform = tender.get("platform", "")
            self.tenders_table.insert(
                "",
                "end",
                values=(title, price, deadline, platform, "Анализ ТЗ"),
                tags=(tender_id,),
            )

    def _on_action_click(self, event) -> None:
        item_id = self.tenders_table.identify_row(event.y)
        if not item_id:
            return
        values = self.tenders_table.item(item_id, "values")
        if not values:
            return
        tender_id = self.tenders_table.item(item_id, "tags")[0] if self.tenders_table.item(item_id, "tags") else ""
        if values[-1] == "Анализ ТЗ":
            self._call_module(
                "modules.specification_analyzer",
                "TenderSpecificationAnalyzer",
                "open_analysis_window",
                tender_id,
                self.active_inn,
            )

    def _manual_entry(self) -> None:
        if not self._ensure_active_inn():
            return
        files = filedialog.askopenfilenames(title="Выберите файлы закупки")
        if not files:
            return
        result = self._call_module(
            "modules.manual_tender_entry",
            "ManualTenderEntry",
            "process_uploaded_files",
            list(files),
            self.active_inn,
        )
        tender = result.get("tender") if isinstance(result, dict) else None
        tender_id = tender.get("number") if isinstance(tender, dict) else None
        if tender_id:
            self._call_module(
                "modules.specification_analyzer",
                "TenderSpecificationAnalyzer",
                "open_analysis_window",
                tender_id,
                self.active_inn,
            )

    def _call_module(self, module_path: str, class_name: str, method: str, *args, default=None):
        try:
            module = importlib.import_module(module_path)
            target_class = getattr(module, class_name)
            target_method = getattr(target_class, method)
            return target_method(*args)
        except ModuleNotFoundError:
            message = f"Модуль не найден: {module_path}"
            self._log(message)
            messagebox.showerror("Ошибка модуля", message)
        except AttributeError:
            message = f"Не найден метод {class_name}.{method}"
            self._log(message)
            messagebox.showerror("Ошибка модуля", message)
        except Exception as exc:  # noqa: BLE001 - логируем для диагностики
            message = f"Ошибка обработки: {exc}"
            self._log(message)
            messagebox.showerror("Ошибка", message)
        return default

    def _log(self, message: str) -> None:
        if not self.log_text:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _load_state(self) -> dict:
        path = self.base_path / STATE_FILE
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _load_config(self) -> dict:
        path = self.base_path / CONFIG_FILE
        if not path.exists():
            return {"mode": "demo"}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"mode": "demo"}

    def _build_title(self) -> str:
        if self.active_inn:
            return f"{APP_TITLE} — ИНН {self.active_inn}"
        return APP_TITLE

    def _on_close(self) -> None:
        self.state["active_inn"] = self.active_inn
        self.state["window_size"] = [self.root.winfo_width(), self.root.winfo_height()]
        (self.base_path / STATE_FILE).write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.root.destroy()

    def _set_actions_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.search_button.configure(state=state)
        self.monitor_button.configure(state=state)
        self.manual_button.configure(state=state)
        self.view_profile_button.configure(state=state)
        self.edit_profile_button.configure(state=state)

    def _ensure_active_inn(self) -> bool:
        if not self.active_inn:
            messagebox.showwarning("Организация", "Сначала выберите организацию.")
            return False
        return True

    def _open_profile_window(self, readonly: bool) -> None:
        if not self._ensure_active_inn():
            return
        profile = self._call_module(
            "modules.organization_manager",
            "OrganizationManager",
            "get_profile",
            self.active_inn,
            default=None,
        )
        if not isinstance(profile, dict):
            return

        window = tk.Toplevel(self.root)
        window.title("Профиль организации")
        window.geometry("720x600")

        container = tk.Frame(window)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries: dict[str, tk.Entry] = {}

        def add_field(label: str, value: str, row: int) -> int:
            tk.Label(scroll_frame, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
            entry = tk.Entry(scroll_frame, width=60)
            entry.insert(0, value)
            if readonly:
                entry.configure(state="readonly")
            entry.grid(row=row, column=1, sticky="w", padx=8, pady=4)
            entries[label] = entry
            return row + 1

        row = 0
        tk.Label(scroll_frame, text="Форма 2: Основные сведения", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8
        )
        row += 1
        for field, value in profile.get("basic_info", {}).items():
            row = add_field(field, str(value), row)

        tk.Label(scroll_frame, text="Классификаторы", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8
        )
        row += 1
        classifiers = profile.get("classifiers", {})
        okved_value = classifiers.get("okved", [])
        okved_text = ", ".join(okved_value) if isinstance(okved_value, list) else str(okved_value)
        row = add_field("okved", okved_text, row)
        for key in ("okpo", "okogu", "oktmo", "kpp"):
            row = add_field(key, str(classifiers.get(key, "")), row)

        tk.Label(scroll_frame, text="Дополнительные поля", font=("Arial", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8
        )
        row += 1
        custom_fields = profile.get("custom_fields", {})
        custom_entries: list[tuple[tk.Entry, tk.Entry]] = []

        for key, value in custom_fields.items():
            key_entry = tk.Entry(scroll_frame, width=25)
            key_entry.insert(0, key)
            value_entry = tk.Entry(scroll_frame, width=35)
            value_entry.insert(0, str(value))
            if readonly:
                key_entry.configure(state="readonly")
                value_entry.configure(state="readonly")
            key_entry.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            value_entry.grid(row=row, column=1, sticky="w", padx=8, pady=4)
            custom_entries.append((key_entry, value_entry))
            row += 1

        if not readonly:
            def add_custom_row() -> None:
                key_entry = tk.Entry(scroll_frame, width=25)
                value_entry = tk.Entry(scroll_frame, width=35)
                key_entry.grid(row=row_holder[0], column=0, sticky="w", padx=8, pady=4)
                value_entry.grid(row=row_holder[0], column=1, sticky="w", padx=8, pady=4)
                custom_entries.append((key_entry, value_entry))
                row_holder[0] += 1

            row_holder = [row]
            tk.Button(scroll_frame, text="Добавить поле", command=add_custom_row).grid(
                row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8
            )
            row_holder[0] += 1

            def save_profile() -> None:
                basic_info = {}
                for field in profile.get("basic_info", {}):
                    basic_info[field] = entries[field].get().strip() or "нет"
                classifiers_data = {
                    "okved": [item.strip() for item in entries["okved"].get().split(",") if item.strip()],
                    "okpo": entries["okpo"].get().strip() or "нет",
                    "okogu": entries["okogu"].get().strip() or "нет",
                    "oktmo": entries["oktmo"].get().strip() or "нет",
                    "kpp": entries["kpp"].get().strip() or "нет",
                }
                custom_data = {}
                for key_entry, value_entry in custom_entries:
                    key = key_entry.get().strip()
                    if key:
                        custom_data[key] = value_entry.get().strip() or "нет"

                updated = {
                    "basic_info": basic_info,
                    "classifiers": classifiers_data,
                    "custom_fields": custom_data,
                }
                profile_path = self.base_path / ORGANIZATIONS_DIR / self.active_inn / "profile.json"
                profile_path.write_text(
                    json.dumps(updated, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                self._log("Профиль организации обновлен.")
                window.destroy()

            tk.Button(window, text="Сохранить", command=save_profile).pack(pady=8)


def main() -> None:
    root = tk.Tk()
    LauncherPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
