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
SEARCH_PARAMS_FILE = "search_parameters.json"
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

    def _build_organization_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Организация", padx=8, pady=8)
        frame.pack(fill="x", pady=6)

        tk.Label(frame, text="Выберите организацию").pack(side="left")
        self.org_var = tk.StringVar(value="Выберите организацию")
        self.org_menu = ttk.Combobox(frame, textvariable=self.org_var, state="readonly", width=30)
        self.org_menu.pack(side="left", padx=8)
        self.org_menu.bind("<<ComboboxSelected>>", self._on_org_selected)

        tk.Button(frame, text="Добавить организацию", command=self._create_organization).pack(
            side="right"
        )

    def _build_search_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Настройки поиска", padx=8, pady=8)
        frame.pack(fill="x", pady=6)

        tk.Button(
            frame,
            text="Открыть параметры поиска",
            command=self._open_search_params_editor,
        ).pack(side="left", padx=4)
        tk.Button(frame, text="Сбросить к умолчаниям", command=self._reset_search_params).pack(
            side="left", padx=4
        )

    def _build_monitoring_block(self) -> None:
        frame = tk.LabelFrame(self.root, text="Мониторинг закупок", padx=8, pady=8)
        frame.pack(fill="both", expand=True, pady=6)

        tk.Button(frame, text="Запустить мониторинг", command=self._run_monitoring).pack(
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

        tk.Button(
            frame,
            text="Добавить закупку вручную",
            command=self._manual_entry,
        ).pack(side="left", padx=4)

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

    def _create_organization(self) -> None:
        self._log("Создание организации...")
        self._call_module(
            "modules.organization_manager",
            "OrganizationManager",
            "create_profile",
        )
        self._load_organizations()

    def _open_search_params_editor(self) -> None:
        self._call_module(
            "modules.tender_monitor",
            "TenderMonitor",
            "open_search_params_editor",
        )

    def _reset_search_params(self) -> None:
        params_path = self.base_path / SEARCH_PARAMS_FILE
        params_path.write_text(
            json.dumps({"keywords": [], "price_min": "", "price_max": ""}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._log("Параметры поиска сброшены к умолчаниям.")

    def _run_monitoring(self) -> None:
        if not self.active_inn:
            messagebox.showwarning("Организация", "Сначала выберите организацию.")
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
            )

    def _manual_entry(self) -> None:
        files = filedialog.askopenfilenames(title="Выберите файлы закупки")
        if not files:
            return
        self._call_module(
            "modules.manual_tender_entry",
            "ManualTenderEntry",
            "process_uploaded_files",
            list(files),
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


def main() -> None:
    root = tk.Tk()
    LauncherPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
