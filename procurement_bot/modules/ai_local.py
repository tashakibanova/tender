"""Local AI analysis using spaCy for Russian."""

from __future__ import annotations

from typing import Dict, List

import spacy


class LocalAIAnalyzer:
    def __init__(self, model_name: str = "ru_core_news_sm") -> None:
        self.nlp = spacy.load(model_name)

    def analyze(self, text: str) -> Dict[str, object]:
        doc = self.nlp(text)
        keywords = sorted({token.lemma_ for token in doc if token.is_alpha and len(token) > 3})
        tender_type = self._guess_tender_type(text)
        return {
            "tender_type": tender_type,
            "keywords": keywords[:20],
            "character_count": len(text),
        }

    def _guess_tender_type(self, text: str) -> str:
        text_lower = text.lower()
        if "запрос котировок" in text_lower:
            return "запрос котировок"
        if "аукцион" in text_lower:
            return "аукцион"
        if "конкурс" in text_lower:
            return "конкурс"
        return "не определено"
