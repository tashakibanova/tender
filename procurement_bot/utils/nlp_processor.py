"""Local NLP processing utilities."""

from __future__ import annotations

from typing import List

import spacy


class NlpProcessor:
    def __init__(self, model_name: str = "ru_core_news_sm") -> None:
        self.nlp = spacy.load(model_name)

    def extract_keywords(self, text: str, limit: int = 15) -> List[str]:
        doc = self.nlp(text)
        keywords = [token.lemma_ for token in doc if token.is_alpha and len(token) > 3]
        unique = []
        for word in keywords:
            if word not in unique:
                unique.append(word)
        return unique[:limit]
