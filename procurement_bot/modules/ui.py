"""Tkinter UI for the procurement bot."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict

from .analysis import TenderAnalysisService
from .documents import DocumentPreparationService
from .monitoring import TenderMonitor
from .profile import ProfileService
from .reporting import ReportService
from .storage import LocalStorage
from .validators import validate_required_fields
from .data_model import UserProfile


class ProcurementApp:
    def __init__(
        self,
        root: tk.Tk,
        storage: LocalStorage,
        profile_service: ProfileService,
        monitor: TenderMonitor,
        analysis_service: TenderAnalysisService,
        document_service: DocumentPreparationService,
        report_service: ReportService,
    ) -> None:
        self.root = root
        self.storage = storage
        self.profile_service = profile_service
        self.monitor = monitor
        self.analysis_service = analysis_service
        self.document_service = document_service
        self.report_service = report_service
        self.profile_entries: Dict[str, tk.Entry] = {}

        self.root.title("Система участия в тендерах")
        self._build_ui()
        self._load_profile()

    def _build_ui(self) -> None:
        self.root.geometry("900x700")
        self.root.configure(padx=20, pady=20)

        title = tk.Label(
            self.root,
            text="Автоматизация участия в тендерах",
            font=("Arial", 18, "bold"),
        )
        title.pack(pady=10)

        profile_frame = tk.LabelFrame(self.root, text="Профиль поставщика", padx=10, pady=10)
        profile_frame.pack(fill="x", pady=10)

        fields = [
            ("company_name", "Наименование компании"),
            ("inn", "ИНН"),
            ("kpp", "КПП"),
            ("ogrn", "ОГРН"),
            ("bank_name", "Банк"),
            ("bank_account", "Расчетный счет"),
            ("correspondent_account", "Корр. счет"),
            ("bik", "БИК"),
            ("address", "Адрес"),
            ("contact_person", "Контактное лицо"),
            ("email", "Email"),
            ("phone", "Телефон"),
            ("keywords", "Ключевые слова (через запятую)"),
        ]

        for field, label in fields:
            row = tk.Frame(profile_frame)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, width=30, anchor="w").pack(side="left")
            entry = tk.Entry(row, width=60)
            entry.pack(side="left", expand=True, fill="x")
            self.profile_entries[field] = entry

        actions_frame = tk.LabelFrame(self.root, text="Действия", padx=10, pady=10)
        actions_frame.pack(fill="x", pady=10)

        tk.Button(actions_frame, text="Сохранить профиль", command=self.save_profile).pack(
            side="left", padx=5
        )
        tk.Button(actions_frame, text="Запустить мониторинг", command=self.run_monitoring).pack(
            side="left", padx=5
        )
        tk.Button(actions_frame, text="Анализировать документ", command=self.analyze_document).pack(
            side="left", padx=5
        )
        tk.Button(actions_frame, text="Подготовить документ", command=self.prepare_document).pack(
            side="left", padx=5
        )
        tk.Button(actions_frame, text="Экспорт отчетов", command=self.export_reports).pack(
            side="left", padx=5
        )

        self.status_label = tk.Label(self.root, text="Готово к работе", anchor="w")
        self.status_label.pack(fill="x", pady=10)

    def _load_profile(self) -> None:
        profile = self.profile_service.load_profile()
        self.profile_entries["company_name"].insert(0, profile.company_name)
        self.profile_entries["inn"].insert(0, profile.inn)
        self.profile_entries["kpp"].insert(0, profile.kpp)
        self.profile_entries["ogrn"].insert(0, profile.ogrn)
        self.profile_entries["bank_name"].insert(0, profile.bank_name)
        self.profile_entries["bank_account"].insert(0, profile.bank_account)
        self.profile_entries["correspondent_account"].insert(0, profile.correspondent_account)
        self.profile_entries["bik"].insert(0, profile.bik)
        self.profile_entries["address"].insert(0, profile.address)
        self.profile_entries["contact_person"].insert(0, profile.contact_person)
        self.profile_entries["email"].insert(0, profile.email)
        self.profile_entries["phone"].insert(0, profile.phone)
        self.profile_entries["keywords"].insert(0, ", ".join(profile.keywords))

    def _collect_profile(self) -> UserProfile:
        data = {field: entry.get().strip() for field, entry in self.profile_entries.items()}
        keywords = [item.strip() for item in data["keywords"].split(",") if item.strip()]
        return UserProfile(
            company_name=data["company_name"],
            inn=data["inn"],
            kpp=data["kpp"],
            ogrn=data["ogrn"],
            bank_name=data["bank_name"],
            bank_account=data["bank_account"],
            correspondent_account=data["correspondent_account"],
            bik=data["bik"],
            address=data["address"],
            contact_person=data["contact_person"],
            email=data["email"],
            phone=data["phone"],
            keywords=keywords,
        )

    def _confirm_action(self, text: str) -> bool:
        return messagebox.askyesno("Подтверждение", text)

    def save_profile(self) -> None:
        if not self._confirm_action("Сохранить профиль? Все поля обязательны."):
            return
        profile = self._collect_profile()
        self.profile_service.save_profile(profile)
        self.status_label.config(text="Профиль сохранен")

    def run_monitoring(self) -> None:
        if not self._confirm_action("Запустить мониторинг по ключевым словам?"):
            return
        profile = self._collect_profile()
        validate_required_fields(profile.__dict__, self.profile_service.REQUIRED_FIELDS)
        lots = self.monitor.run_monitoring_cycle(profile.keywords)
        self.status_label.config(text=f"Найдено лотов: {len(lots)}")

    def analyze_document(self) -> None:
        if not self._confirm_action("Запустить анализ документа?"):
            return
        file_path = filedialog.askopenfilename(
            title="Выберите документ ТЗ",
            filetypes=[("Документы", "*.pdf *.docx *.txt")],
        )
        if not file_path:
            return
        result = self.analysis_service.analyze_document(file_path)
        messagebox.showinfo("Результат анализа", f"Тип закупки: {result.get('tender_type')}")
        self.status_label.config(text="Анализ завершен")

    def prepare_document(self) -> None:
        if not self._confirm_action("Подготовить документ по шаблону?"):
            return
        template_path = filedialog.askopenfilename(
            title="Выберите шаблон DOCX",
            filetypes=[("Шаблоны", "*.docx")],
        )
        if not template_path:
            return
        output_path = filedialog.asksaveasfilename(
            title="Сохранить готовый документ",
            defaultextension=".docx",
            filetypes=[("Документ", "*.docx")],
        )
        if not output_path:
            return
        profile = self._collect_profile()
        payload = {
            "НАИМЕНОВАНИЕ": profile.company_name,
            "ИНН": profile.inn,
            "ЦЕНА": "",
        }
        self.document_service.fill_template(template_path, output_path, payload)
        self.status_label.config(text="Документ подготовлен и открыт для ручной правки")

    def export_reports(self) -> None:
        if not self._confirm_action("Сформировать локальные отчеты?"):
            return
        excel_path = self.report_service.export_lots_to_excel()
        json_path = self.report_service.export_lots_to_json()
        messagebox.showinfo(
            "Отчеты готовы",
            f"Excel: {excel_path}\nJSON: {json_path}",
        )
        self.status_label.config(text="Отчеты сохранены")
