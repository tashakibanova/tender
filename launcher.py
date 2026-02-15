"""Launcher: единственная точка входа для приложения на Tkinter.

Запуск:
    python launcher.py

Ограничения:
- Используется только стандартная библиотека Python.
- Все пути относительные (./organizations/).
"""

import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Платформа для госзакупок — Лаунчер"
WINDOW_SIZE = "900x600"
STATE_FILE = "launcher_state.json"
ORGANIZATIONS_DIR = "organizations"
PROFILE_FILE = "profile.json"
SEARCH_KEYWORDS_FILE = "search_keywords.json"

MODE_LABELS = {
    "exact": "точное совпадение",
    "nearby": "слова рядом",
    "any_ending": "любые окончания",
}
MODE_KEYS = {value: key for key, value in MODE_LABELS.items()}

PROFILE_FIELDS = [
    "Наименование",
    "Дата регистрации",
    "Адрес местонахождения",
    "Почтовый адрес",
    "Фактический адрес",
    "ФИО руководителя",
    "Должность руководителя",
    "Телефон",
    "Факс",
    "Email",
    "Сайт",
    "ИНН",
    "КПП",
    "Банковские реквизиты",
    "Сведения об одобрении сделки",
]


class LauncherApp:
    """Минимальный, но рабочий Tkinter-лаунчер."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.organizations_path = os.path.join(self.base_path, ORGANIZATIONS_DIR)
        os.makedirs(self.organizations_path, exist_ok=True)

        self.active_inn = ""
        self._load_state()

        self._build_ui()
        self._load_organizations()
        self._maybe_prompt_first_org()
        self._update_action_state()

    def _build_ui(self) -> None:
        self.root.configure(padx=12, pady=12)

        self.org_frame = tk.LabelFrame(self.root, text="Организация", padx=8, pady=8)
        self.org_frame.pack(fill="x", pady=6)
        self._build_org_block()

        self.search_frame = tk.LabelFrame(self.root, text="Параметры поиска", padx=8, pady=8)
        self.search_frame.pack(fill="x", pady=6)
        self._build_search_block()

        self.monitor_frame = tk.LabelFrame(self.root, text="Мониторинг закупок", padx=8, pady=8)
        self.monitor_frame.pack(fill="both", expand=True, pady=6)
        self._build_monitor_block()

        self.manual_frame = tk.LabelFrame(self.root, text="Ручной ввод", padx=8, pady=8)
        self.manual_frame.pack(fill="x", pady=6)
        self._build_manual_block()

        self.log_frame = tk.LabelFrame(self.root, text="Журнал событий", padx=8, pady=8)
        self.log_frame.pack(fill="both", pady=6)
        self.log_text = tk.Text(self.log_frame, height=6, state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def _build_org_block(self) -> None:
        tk.Label(self.org_frame, text="Выберите организацию").pack(side="left")
        self.org_var = tk.StringVar(value="Выберите организацию")
        self.org_menu = ttk.Combobox(
            self.org_frame,
            textvariable=self.org_var,
            state="readonly",
            width=30,
        )
        self.org_menu.pack(side="left", padx=8)
        self.org_menu.bind("<<ComboboxSelected>>", self._on_org_selected)

        tk.Button(self.org_frame, text="Добавить организацию", command=self._create_organization).pack(
            side="right", padx=4
        )
        self.view_profile_button = tk.Button(
            self.org_frame,
            text="Просмотреть профиль",
            command=lambda: self._open_profile_window(readonly=True),
        )
        self.view_profile_button.pack(side="right", padx=4)
        self.edit_profile_button = tk.Button(
            self.org_frame,
            text="Изменить реквизиты",
            command=lambda: self._open_profile_window(readonly=False),
        )
        self.edit_profile_button.pack(side="right", padx=4)

    def _build_search_block(self) -> None:
        self.search_button = tk.Button(
            self.search_frame,
            text="Настроить ключевые слова",
            command=self._open_search_keywords_editor,
        )
        self.search_button.pack(side="left", padx=4)

    def _build_monitor_block(self) -> None:
        self.monitor_button = tk.Button(
            self.monitor_frame,
            text="Запустить мониторинг",
            command=self._run_monitoring,
        )
        self.monitor_button.pack(anchor="w", pady=4)

        columns = ("title", "price", "deadline", "platform", "action")
        self.tenders_table = ttk.Treeview(self.monitor_frame, columns=columns, show="headings", height=6)
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
        self.manual_button = tk.Button(
            self.manual_frame,
            text="Добавить закупку вручную",
            command=self._manual_entry,
        )
        self.manual_button.pack(side="left", padx=4)

    def _load_organizations(self) -> None:
        organizations = []
        if os.path.isdir(self.organizations_path):
            for name in sorted(os.listdir(self.organizations_path)):
                path = os.path.join(self.organizations_path, name)
                if os.path.isdir(path):
                    organizations.append(name)
        if not organizations:
            organizations = ["Выберите организацию"]
        self.org_menu["values"] = organizations
        if self.active_inn and self.active_inn in organizations:
            self.org_var.set(self.active_inn)
        else:
            self.org_var.set(organizations[0])

    def _maybe_prompt_first_org(self) -> None:
        if os.path.isdir(self.organizations_path) and not os.listdir(self.organizations_path):
            if messagebox.askyesno("Организация", "Папка организаций пуста. Создать первую организацию?"):
                self._create_organization()

    def _on_org_selected(self, _event=None) -> None:
        selection = self.org_var.get()
        if selection and selection != "Выберите организацию":
            self.active_inn = selection
            self._log(f"Загружена организация: {selection}")
        else:
            self.active_inn = ""
        self._update_action_state()

    def _create_organization(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая организация")
        dialog.geometry("420x220")
        dialog.grab_set()

        tk.Label(dialog, text="ИНН (обязательно)").pack(anchor="w", padx=12, pady=6)
        inn_var = tk.StringVar()
        tk.Entry(dialog, textvariable=inn_var).pack(fill="x", padx=12)

        tk.Label(dialog, text="Наименование").pack(anchor="w", padx=12, pady=6)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var).pack(fill="x", padx=12)

        def submit() -> None:
            inn = inn_var.get().strip()
            if not inn:
                messagebox.showwarning("Организация", "ИНН обязателен.")
                return
            org_dir = os.path.join(self.organizations_path, inn)
            if os.path.exists(org_dir):
                messagebox.showwarning("Организация", "Организация с таким ИНН уже существует.")
                return
            os.makedirs(org_dir, exist_ok=True)
            profile = {field: "нет" for field in PROFILE_FIELDS}
            profile["Наименование"] = name_var.get().strip() or "нет"
            profile["ИНН"] = inn
            profile_path = os.path.join(org_dir, PROFILE_FILE)
            self._write_json(profile_path, profile)

            keywords_path = os.path.join(org_dir, SEARCH_KEYWORDS_FILE)
            self._write_json(keywords_path, {"terms": []})

            self.active_inn = inn
            self._load_organizations()
            self._update_action_state()
            self._log(f"Создана организация: {inn}")
            dialog.destroy()

        tk.Button(dialog, text="Создать", command=submit).pack(pady=12)

    def _open_profile_window(self, readonly: bool) -> None:
        if not self._ensure_active_inn():
            return
        profile_path = os.path.join(self.organizations_path, self.active_inn, PROFILE_FILE)
        profile = self._read_json(profile_path)
        if not isinstance(profile, dict):
            profile = {field: "нет" for field in PROFILE_FIELDS}

        window = tk.Toplevel(self.root)
        window.title("Профиль организации")
        window.geometry("720x560")

        canvas = tk.Canvas(window)
        scrollbar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries = {}
        row = 0
        for field in PROFILE_FIELDS:
            tk.Label(scroll_frame, text=field).grid(row=row, column=0, sticky="w", padx=8, pady=4)
            entry = tk.Entry(scroll_frame, width=60)
            entry.insert(0, profile.get(field, "нет"))
            if readonly:
                entry.configure(state="readonly")
            entry.grid(row=row, column=1, sticky="w", padx=8, pady=4)
            entries[field] = entry
            row += 1

        if not readonly:
            def save_profile() -> None:
                updated = {field: entries[field].get().strip() or "нет" for field in PROFILE_FIELDS}
                self._write_json(profile_path, updated)
                self._log("Профиль организации обновлен.")
                window.destroy()

            tk.Button(window, text="Сохранить", command=save_profile).pack(pady=8)

    def _open_search_keywords_editor(self) -> None:
        if not self._ensure_active_inn():
            return
        keywords_path = os.path.join(self.organizations_path, self.active_inn, SEARCH_KEYWORDS_FILE)
        data = self._read_json(keywords_path)
        if not isinstance(data, dict):
            data = {"terms": []}
        terms = data.get("terms", [])
        if isinstance(terms, list) and terms and isinstance(terms[0], str):
            terms = [{"term": item, "mode": "exact"} for item in terms]

        window = tk.Toplevel(self.root)
        window.title("Ключевые слова")
        window.geometry("560x420")

        listbox = tk.Listbox(window, height=10)
        listbox.pack(fill="both", expand=True, padx=8, pady=8)

        mode_var = tk.StringVar(value=MODE_LABELS["exact"])
        mode_menu = ttk.Combobox(window, textvariable=mode_var, values=list(MODE_LABELS.values()), state="readonly")
        mode_menu.pack(anchor="w", padx=8)

        entry_var = tk.StringVar()
        entry = tk.Entry(window, textvariable=entry_var)
        entry.pack(fill="x", padx=8, pady=6)

        def refresh_list() -> None:
            listbox.delete(0, "end")
            for item in terms:
                label = f"{item.get('term', '')} ({MODE_LABELS.get(item.get('mode', 'exact'), MODE_LABELS['exact'])})"
                listbox.insert("end", label)

        def add_term() -> None:
            term = entry_var.get().strip()
            if not term:
                return
            mode_label = mode_var.get()
            terms.append({"term": term, "mode": MODE_KEYS.get(mode_label, "exact")})
            entry_var.set("")
            refresh_list()

        def remove_term() -> None:
            selection = listbox.curselection()
            if not selection:
                return
            index = selection[0]
            terms.pop(index)
            refresh_list()

        def save_terms() -> None:
            self._write_json(keywords_path, {"terms": terms})
            self._log("Ключевые слова сохранены.")
            window.destroy()

        btn_frame = tk.Frame(window)
        btn_frame.pack(fill="x", padx=8, pady=4)
        tk.Button(btn_frame, text="+", width=4, command=add_term).pack(side="left")
        tk.Button(btn_frame, text="–", width=4, command=remove_term).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Сохранить", command=save_terms).pack(side="right")

        refresh_list()

    def _run_monitoring(self) -> None:
        if not self._ensure_active_inn():
            return
        tenders = self._call_module_function("modules.tender_monitor", "find_tenders", [self.active_inn], default=[])
        self._render_tenders(tenders)
        self._log(f"Найдено лотов: {len(tenders)}")

    def _render_tenders(self, tenders: list) -> None:
        for item in self.tenders_table.get_children():
            self.tenders_table.delete(item)
        for tender in tenders:
            tender_id = tender.get("id", "")
            self.tenders_table.insert(
                "",
                "end",
                values=(
                    tender.get("title", ""),
                    tender.get("price", ""),
                    tender.get("deadline", ""),
                    tender.get("platform", ""),
                    "Анализ ТЗ",
                ),
                tags=(tender_id,),
            )

    def _on_action_click(self, event) -> None:
        item_id = self.tenders_table.identify_row(event.y)
        if not item_id:
            return
        tender_id = ""
        tags = self.tenders_table.item(item_id, "tags")
        if tags:
            tender_id = tags[0]
        if tender_id:
            self._call_module_function(
                "modules.specification_analyzer",
                "open_analysis_window",
                [tender_id, self.active_inn],
                default=None,
            )

    def _manual_entry(self) -> None:
        if not self._ensure_active_inn():
            return
        files = filedialog.askopenfilenames(
            title="Выберите файлы закупки",
            filetypes=[
                ("Документы", "*.pdf *.docx *.xlsx *.xls *.jpg *.jpeg *.png *.zip"),
                ("Все файлы", "*.*"),
            ],
        )
        if not files:
            return
        result = self._call_module_function(
            "modules.manual_tender_entry",
            "process_files",
            [list(files), self.active_inn],
            default=None,
        )
        if isinstance(result, dict):
            tender_id = result.get("tender_id") or result.get("id")
            if tender_id:
                self._call_module_function(
                    "modules.specification_analyzer",
                    "open_analysis_window",
                    [tender_id, self.active_inn],
                    default=None,
                )

    def _call_module_function(self, module_name: str, func_name: str, args: list, default=None):
        try:
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)
            return func(*args)
        except ModuleNotFoundError:
            self._log(
                f"Ошибка: модуль {module_name} не найден. Убедитесь, что папка /modules/ существует."
            )
        except AttributeError:
            self._log(f"Ошибка: функция {func_name} не найдена в модуле {module_name}.")
        except Exception as exc:
            self._log(f"Ошибка обработки: {exc}")
        return default

    def _update_action_state(self) -> None:
        enabled = bool(self.active_inn)
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

    def _load_state(self) -> None:
        path = os.path.join(self.base_path, STATE_FILE)
        data = self._read_json(path)
        if isinstance(data, dict):
            self.active_inn = data.get("active_inn", "")

    def _on_close(self) -> None:
        state = {"active_inn": self.active_inn, "updated_at": datetime.now().isoformat()}
        path = os.path.join(self.base_path, STATE_FILE)
        self._write_json(path, state)
        self.root.destroy()

    def _read_json(self, path: str):
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

    def _write_json(self, path: str, data) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")


def main() -> None:
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
