"""Document analysis module with local NLP processing."""

from __future__ import annotations

from typing import Dict

from .ai_local import LocalAIAnalyzer
from .storage import LocalStorage
from utils.file_parser import extract_text


class TenderAnalysisService:
    def __init__(self, storage: LocalStorage, analyzer: LocalAIAnalyzer) -> None:
        self.storage = storage
        self.analyzer = analyzer

    def analyze_document(self, file_path: str) -> Dict[str, object]:
        text = extract_text(file_path)
        analysis = self.analyzer.analyze(text)
        self.storage.write_json("data/analysis_result.json", analysis)
        return analysis
