"""ManualTenderEntry: ручное добавление закупок и обработка документов."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from xml.etree import ElementTree

try:
    import rarfile
except ImportError:  # pragma: no cover - опционально
    rarfile = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - опционально
    Image = None


class ManualTenderEntry:
    """Обеспечивает ручной ввод закупок и обработку входящих файлов."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ORGANIZATIONS_DIR = os.path.join(BASE_DIR, "organizations")

    ALLOWED_DOCS = {".pdf", ".docx", ".txt"}
    ALLOWED_TABLES = {".xlsx", ".xls", ".csv"}
    ALLOWED_IMAGES = {".jpg", ".jpeg", ".png", ".tiff", ".bmp"}
    ALLOWED_ARCHIVES = {".zip", ".rar"}
    BLOCKED_EXTENSIONS = {".exe", ".bat", ".vbs"}

    @classmethod
    def process_uploaded_files(cls, file_paths: list, inn: str | None = None) -> dict:
        """Обрабатывает список файлов и возвращает метаданные обработки."""
        inn = inn or cls._load_active_inn()
        if not inn:
            raise ValueError("Не указан ИНН для сохранения закупки.")

        extracted_texts: list[str] = []
        product_candidates: list[dict] = []
        processed_files: list[dict] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            for path in file_paths:
                extracted = cls._process_single_file(path, temp_dir)
                extracted_texts.append(extracted["text"])
                product_candidates.extend(extracted.get("product_candidates", []))
                processed_files.append(extracted["metadata"])

        combined_text = "\n".join(filter(None, extracted_texts))
        auto_fields = cls._extract_fields_from_text(combined_text)
        tender_data = cls._build_tender_data(auto_fields)
        registry_record = cls._save_manual_tender(inn, tender_data, combined_text, processed_files)
        cls._save_product_candidates(inn, tender_data["tender_id_or_url"], product_candidates)

        return {
            "tender": registry_record,
            "extracted_text": combined_text,
            "product_candidates": product_candidates,
            "files": processed_files,
        }

    @classmethod
    def get_extracted_text(cls, inn: str, tender_id: str) -> str:
        """Возвращает извлеченный текст по идентификатору закупки."""
        extracted_path = os.path.join(
            cls._tender_dir(inn, tender_id), "extracted", "text.txt"
        )
        if not os.path.exists(extracted_path):
            return ""
        with open(extracted_path, "r", encoding="utf-8") as file:
            return file.read()

    @classmethod
    def get_product_candidates(cls, inn: str, tender_id: str) -> list[dict]:
        """Возвращает найденные товарные позиции по закупке."""
        candidates_path = os.path.join(
            cls._tender_dir(inn, tender_id), "extracted", "product_candidates.json"
        )
        if not os.path.exists(candidates_path):
            return []
        with open(candidates_path, "r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def _process_single_file(cls, path: str, temp_dir: str) -> dict:
        extension = os.path.splitext(path)[1].lower()
        if extension in cls.BLOCKED_EXTENSIONS:
            return cls._metadata(path, extension, blocked=True, text="")

        if extension in cls.ALLOWED_ARCHIVES:
            return cls._process_archive(path, temp_dir)

        if extension in cls.ALLOWED_IMAGES:
            text = cls._extract_text_from_image(path)
            candidates = cls._extract_product_candidates(text)
            return cls._metadata(path, extension, text=text, product_candidates=candidates)

        if extension in cls.ALLOWED_TABLES:
            text = cls._extract_text_from_table(path)
            candidates = cls._extract_product_candidates(text)
            return cls._metadata(path, extension, text=text, product_candidates=candidates)

        if extension in cls.ALLOWED_DOCS:
            text = cls._extract_text_from_document(path)
            candidates = cls._extract_product_candidates(text)
            return cls._metadata(path, extension, text=text, product_candidates=candidates)

        return cls._metadata(path, extension, text="")

    @classmethod
    def _process_archive(cls, path: str, temp_dir: str) -> dict:
        extension = os.path.splitext(path)[1].lower()
        extracted_texts: list[str] = []
        candidates: list[dict] = []
        metadata = {"file": path, "type": extension, "blocked": False}

        if extension == ".zip":
            with zipfile.ZipFile(path, "r") as archive:
                archive.extractall(temp_dir)
        elif extension == ".rar" and rarfile:
            with rarfile.RarFile(path) as archive:  # type: ignore[attr-defined]
                archive.extractall(temp_dir)
        else:
            metadata["error"] = "Архив RAR не поддерживается"
            return {"text": "", "product_candidates": [], "metadata": metadata}

        for root, _dirs, files in os.walk(temp_dir):
            for name in files:
                nested_path = os.path.join(root, name)
                nested = cls._process_single_file(nested_path, temp_dir)
                extracted_texts.append(nested["text"])
                candidates.extend(nested.get("product_candidates", []))

        metadata["processed_files"] = len(extracted_texts)
        return {
            "text": "\n".join(filter(None, extracted_texts)),
            "product_candidates": candidates,
            "metadata": metadata,
        }

    @staticmethod
    def _extract_text_from_document(path: str) -> str:
        if path.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                return file.read()
        if path.lower().endswith(".docx"):
            return ManualTenderEntry._extract_text_from_docx(path)
        return ""

    @staticmethod
    def _extract_text_from_docx(path: str) -> str:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                xml_content = archive.read("word/document.xml")
        except (KeyError, zipfile.BadZipFile):
            return ""
        root = ElementTree.fromstring(xml_content)
        texts = []
        for node in root.iter():
            if node.text and node.tag.endswith("}t"):
                texts.append(node.text)
        return "\n".join(texts)

    @staticmethod
    def _extract_text_from_table(path: str) -> str:
        extension = os.path.splitext(path)[1].lower()
        if extension == ".csv":
            return ManualTenderEntry._extract_text_from_csv(path)
        if extension == ".xlsx":
            return ManualTenderEntry._extract_text_from_xlsx(path)
        return ""

    @staticmethod
    def _extract_text_from_csv(path: str) -> str:
        rows = []
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            reader = csv.reader(file)
            for row in reader:
                rows.append(" ".join(row))
        return "\n".join(rows)

    @staticmethod
    def _extract_text_from_xlsx(path: str) -> str:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                shared = {}
                if "xl/sharedStrings.xml" in archive.namelist():
                    shared_xml = archive.read("xl/sharedStrings.xml")
                    shared_root = ElementTree.fromstring(shared_xml)
                    shared = {
                        idx: node.text or ""
                        for idx, node in enumerate(shared_root.iter())
                        if node.tag.endswith("}t")
                    }
                sheet_name = next(
                    (name for name in archive.namelist() if name.startswith("xl/worksheets")),
                    None,
                )
                if not sheet_name:
                    return ""
                sheet_xml = archive.read(sheet_name)
        except (KeyError, zipfile.BadZipFile, StopIteration):
            return ""

        root = ElementTree.fromstring(sheet_xml)
        values: list[str] = []
        for cell in root.iter():
            if cell.tag.endswith("}v") and cell.text:
                if cell.text.isdigit() and int(cell.text) in shared:
                    values.append(shared[int(cell.text)])
                else:
                    values.append(cell.text)
        return "\n".join(values)

    @staticmethod
    def _extract_text_from_image(path: str) -> str:
        if Image is None:
            return ""
        image = Image.open(path).convert("L")
        image = image.point(lambda value: 255 if value > 160 else 0)
        return ManualTenderEntry._simple_ocr_placeholder(image)

    @staticmethod
    def _simple_ocr_placeholder(_image) -> str:
        """Простая заглушка OCR (без внешних зависимостей)."""
        return ""

    @classmethod
    def _extract_fields_from_text(cls, text: str) -> dict:
        fields = {}
        inn_match = re.search(r"ИНН заказчика[:\\s]+(\\d{10,12})", text, re.IGNORECASE)
        if inn_match:
            fields["customer_inn"] = inn_match.group(1)
        deadline_match = re.search(
            r"Срок исполнения[:\\s]+(\\d{2}\\.\\d{2}\\.\\d{4}\\s\\d{2}:\\d{2})",
            text,
            re.IGNORECASE,
        )
        if deadline_match:
            fields["submission_deadline"] = deadline_match.group(1)
        return fields

    @staticmethod
    def _build_tender_data(fields: dict) -> dict:
        tender_id = fields.get("tender_id_or_url") or fields.get("customer_inn") or "manual"
        submission_deadline = fields.get("submission_deadline") or datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        )
        return {
            "tender_id_or_url": tender_id,
            "title": fields.get("title", "Ручная закупка"),
            "submission_deadline": submission_deadline,
            "nmck": float(fields.get("nmck", 0)),
            "type": fields.get("type", "товар"),
            "region": fields.get("region", ""),
            "customer_name": fields.get("customer_name", ""),
            "contact_person": fields.get("contact_person", ""),
        }

    @classmethod
    def _save_manual_tender(
        cls,
        inn: str,
        tender: dict,
        extracted_text: str,
        files_metadata: list[dict],
    ) -> dict:
        tender_id = tender["tender_id_or_url"]
        tender_dir = cls._tender_dir(inn, tender_id)
        original_dir = os.path.join(tender_dir, "manual_docs", "original")
        extracted_dir = os.path.join(tender_dir, "extracted")
        os.makedirs(original_dir, exist_ok=True)
        os.makedirs(extracted_dir, exist_ok=True)

        metadata_path = os.path.join(tender_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump({"files": files_metadata}, file, ensure_ascii=False, indent=2)

        text_path = os.path.join(extracted_dir, "text.txt")
        with open(text_path, "w", encoding="utf-8") as file:
            file.write(extracted_text)

        status = cls._evaluate_status(tender["submission_deadline"])
        record = {
            "number": tender_id,
            "title": tender["title"],
            "price": tender["nmck"],
            "deadline": tender["submission_deadline"],
            "url": tender["tender_id_or_url"],
            "platform": "manual",
            "status": status,
        }
        cls._save_registry_record(inn, record)
        return record

    @classmethod
    def _save_registry_record(cls, inn: str, record: dict) -> None:
        registry_path = os.path.join(cls._lots_dir(inn), "registry.json")
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        existing = []
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as file:
                existing = json.load(file)
        existing_ids = {item.get("number") for item in existing}
        if record["number"] not in existing_ids:
            existing.append(record)
            with open(registry_path, "w", encoding="utf-8") as file:
                json.dump(existing, file, ensure_ascii=False, indent=2)

    @classmethod
    def _save_product_candidates(cls, inn: str, tender_id: str, candidates: list[dict]) -> None:
        extracted_dir = os.path.join(cls._tender_dir(inn, tender_id), "extracted")
        os.makedirs(extracted_dir, exist_ok=True)
        candidates_path = os.path.join(extracted_dir, "product_candidates.json")
        with open(candidates_path, "w", encoding="utf-8") as file:
            json.dump(candidates, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _extract_product_candidates(text: str) -> list[dict]:
        candidates = []
        pattern = re.compile(r"(артикул|арт\\.?)[\\s:]+(?P<code>\\w+).*?(?P<price>\\d+[\\s\\d.,]*)", re.IGNORECASE)
        for match in pattern.finditer(text):
            candidates.append(
                {
                    "code": match.group("code"),
                    "price": match.group("price").replace(" ", ""),
                }
            )
        return candidates

    @staticmethod
    def _evaluate_status(deadline: str) -> str:
        try:
            end_time = datetime.strptime(deadline, "%d.%m.%Y %H:%M")
        except ValueError:
            return "актуальна"
        return "просрочена" if end_time <= datetime.now() else "актуальна"

    @classmethod
    def _metadata(
        cls,
        path: str,
        extension: str,
        text: str,
        blocked: bool = False,
        product_candidates: list | None = None,
    ) -> dict:
        return {
            "text": text,
            "product_candidates": product_candidates or [],
            "metadata": {
                "file": path,
                "type": extension,
                "blocked": blocked,
            },
        }

    @classmethod
    def _lots_dir(cls, inn: str) -> str:
        return os.path.join(cls.ORGANIZATIONS_DIR, inn, "lots")

    @classmethod
    def _tender_dir(cls, inn: str, tender_id: str) -> str:
        return os.path.join(cls._lots_dir(inn), str(tender_id))

    @classmethod
    def _load_active_inn(cls) -> str:
        state_path = os.path.join(cls.BASE_DIR, "launcher_state.json")
        if not os.path.exists(state_path):
            return ""
        with open(state_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("active_inn", "")
