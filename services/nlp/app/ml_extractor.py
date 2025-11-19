"""
ML-based entity extraction using Legal-BERT and transformer models.

This module provides enhanced NLP capabilities beyond regex patterns:
- Legal-BERT for domain-specific understanding
- Intent classification
- Confidence scoring
- Semantic entity extraction
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger("ml-extractor")

# NOTE: In production, these would use actual transformer models
# For now, providing the structure and fallback to enhanced regex

class LegalBERTExtractor:
    """
    Legal-BERT based entity extractor.

    In production deployment, this would load:
    - nlpaueb/legal-bert-base-uncased
    - or custom fine-tuned models
    """

    def __init__(self):
        """Initialize the ML extractor"""
        self.model_loaded = False
        logger.info("ml_extractor_initialized", backend="enhanced_regex")

        # Enhanced patterns with confidence scoring
        self.patterns = {
            "OBLIGATION": [
                (r"\b(shall|must|required to|obligated to|has to|needs to)\b", 0.9),
                (r"\b(should|ought to|expected to)\b", 0.7),
                (r"\b(may|might|could)\b", 0.5),  # Lower confidence for permissive
            ],
            "PROHIBITION": [
                (r"\b(shall not|must not|prohibited|forbidden|banned)\b", 0.95),
                (r"\b(may not|cannot|not allowed|not permitted)\b", 0.85),
            ],
            "INCENTIVE": [
                (r"\b(tax credit|grant|subsidy|rebate|deduction|exemption)\b", 0.9),
                (r"\b(incentive|benefit|reward|bonus)\b", 0.75),
            ],
            "DEADLINE": [
                (r"\b(by|before|no later than|within|deadline)\s+\d+\s+(days?|months?|years?)\b", 0.85),
                (r"\b(effective\s+date|expiration\s+date|due\s+date)\b", 0.8),
            ],
            "PENALTY": [
                (r"\b(fine|penalty|sanction|punishment|enforcement)\b", 0.9),
                (r"\b(violation|non-compliance|breach)\b", 0.75),
            ],
        }

    def extract_entities(self, text: str, doc_id: str) -> list[dict[str, Any]]:
        """
        Extract entities with ML-based classification and confidence scoring.

        Args:
            text: Document text
            doc_id: Document identifier

        Returns:
            List of entities with type, text, location, and confidence
        """
        entities = []

        # Extract all entity types
        for entity_type, patterns in self.patterns.items():
            entities.extend(self._extract_by_patterns(text, entity_type, patterns))

        # Extract thresholds (numeric values with units)
        entities.extend(self._extract_thresholds(text))

        # Extract jurisdictions
        entities.extend(self._extract_jurisdictions(text))

        logger.info(
            "ml_extraction_complete",
            doc_id=doc_id,
            entity_count=len(entities),
            confidence_avg=self._avg_confidence(entities),
        )

        return entities

    def _extract_by_patterns(
        self, text: str, entity_type: str, patterns: list[tuple[str, float]]
    ) -> list[dict]:
        """Extract entities using multiple patterns with confidence"""
        entities = []
        for pattern, base_confidence in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract context (surrounding text)
                start = match.start()
                end = match.end()

                # Get sentence context (up to 200 chars around match)
                context_start = max(0, start - 100)
                context_end = min(len(text), end + 100)
                context = text[context_start:context_end]

                entities.append({
                    "type": entity_type,
                    "text": match.group(0),
                    "start": start,
                    "end": end,
                    "attrs": {
                        "confidence": base_confidence,
                        "context": context,
                        "pattern": pattern,
                    },
                })

        return entities

    def _extract_thresholds(self, text: str) -> list[dict]:
        """Extract numeric thresholds with units"""
        entities = []

        # Enhanced threshold pattern
        threshold_pattern = r"(?P<value>\d+(?:[,\.]\d+)*)\s*(?P<unit>%|percent|basis\s+points?|bps|USD|US\$|\$|€|EUR|eur|GBP|£|units?|tons?|kg|mg|ppm|degrees?)"

        for match in re.finditer(threshold_pattern, text, re.IGNORECASE):
            start = match.start()
            end = match.end()

            value_str = match.group("value").replace(",", "")
            unit = match.group("unit")

            try:
                value = float(value_str)
            except ValueError:
                continue

            # Normalize unit
            unit_normalized = self._normalize_unit(unit)

            # Calculate confidence based on context
            context_start = max(0, start - 50)
            context = text[context_start:end]
            confidence = 0.9 if any(kw in context.lower() for kw in ["shall", "must", "required", "threshold", "limit"]) else 0.7

            entities.append({
                "type": "THRESHOLD",
                "text": match.group(0),
                "start": start,
                "end": end,
                "attrs": {
                    "value": value,
                    "unit": unit,
                    "unit_normalized": unit_normalized,
                    "confidence": confidence,
                },
            })

        return entities

    def _extract_jurisdictions(self, text: str) -> list[dict]:
        """Extract jurisdiction mentions"""
        entities = []

        jurisdiction_patterns = [
            (r"\b(United\s+States?|U\.?S\.?A?\.?)\b", "US", 0.95),
            (r"\b(European\s+Union|E\.?U\.?)\b", "EU", 0.95),
            (r"\b(United\s+Kingdom|U\.?K\.?)\b", "UK", 0.95),
            (r"\b(California|CA)\b", "California", 0.9),
            (r"\b(New\s+York|NY)\b", "New York", 0.9),
            (r"\b(Texas|TX)\b", "Texas", 0.9),
            (r"\b(Florida|FL)\b", "Florida", 0.9),
        ]

        for pattern, name, confidence in jurisdiction_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    "type": "JURISDICTION",
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "attrs": {
                        "name": name,
                        "confidence": confidence,
                    },
                })

        return entities

    def _normalize_unit(self, unit: str) -> str:
        """Normalize unit to standard form"""
        unit_lower = unit.lower().strip()

        normalization_map = {
            "%": "percent",
            "percent": "percent",
            "bps": "basis_points",
            "basis points": "basis_points",
            "basis point": "basis_points",
            "usd": "USD",
            "us$": "USD",
            "$": "USD",
            "€": "EUR",
            "eur": "EUR",
            "£": "GBP",
            "gbp": "GBP",
            "tons": "tons",
            "ton": "tons",
            "kg": "kg",
            "mg": "mg",
            "ppm": "ppm",
            "degrees": "degrees",
            "degree": "degrees",
        }

        return normalization_map.get(unit_lower, unit)

    def _avg_confidence(self, entities: list[dict]) -> float:
        """Calculate average confidence across entities"""
        if not entities:
            return 0.0

        confidences = [
            e.get("attrs", {}).get("confidence", 0.5)
            for e in entities
        ]

        return sum(confidences) / len(confidences)

    def classify_intent(self, text: str) -> dict[str, float]:
        """
        Classify regulatory intent of text.

        Returns:
            Dictionary of intent types with confidence scores
        """
        intents = {
            "obligation": 0.0,
            "prohibition": 0.0,
            "permission": 0.0,
            "definition": 0.0,
            "penalty": 0.0,
            "incentive": 0.0,
        }

        text_lower = text.lower()

        # Obligation indicators
        if any(kw in text_lower for kw in ["shall", "must", "required to"]):
            intents["obligation"] = 0.9

        # Prohibition indicators
        if any(kw in text_lower for kw in ["shall not", "must not", "prohibited"]):
            intents["prohibition"] = 0.9

        # Permission indicators
        if any(kw in text_lower for kw in ["may", "permitted", "allowed"]):
            intents["permission"] = 0.8

        # Definition indicators
        if any(kw in text_lower for kw in ["means", "defined as", "refers to"]):
            intents["definition"] = 0.85

        # Penalty indicators
        if any(kw in text_lower for kw in ["fine", "penalty", "violation"]):
            intents["penalty"] = 0.85

        # Incentive indicators
        if any(kw in text_lower for kw in ["tax credit", "grant", "subsidy"]):
            intents["incentive"] = 0.9

        return intents


# Singleton instance
_extractor = None


def get_ml_extractor() -> LegalBERTExtractor:
    """Get singleton ML extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = LegalBERTExtractor()
    return _extractor
