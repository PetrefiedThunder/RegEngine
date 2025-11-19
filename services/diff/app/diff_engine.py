"""
Core diff engine for regulatory document comparison.

Detects:
- Added sections
- Removed sections
- Modified text
- Threshold changes
- Obligation changes
"""

from __future__ import annotations

import difflib
import re
from typing import Any

import structlog

logger = structlog.get_logger("diff-engine")


class DocumentDiff:
    """Document comparison results"""

    def __init__(self, doc1: dict, doc2: dict):
        self.doc1 = doc1
        self.doc2 = doc2
        self.changes = []

    def add_change(
        self,
        change_type: str,
        description: str,
        old_value: Any = None,
        new_value: Any = None,
        location: str | None = None,
    ):
        """Add a detected change"""
        self.changes.append(
            {
                "type": change_type,
                "description": description,
                "old_value": old_value,
                "new_value": new_value,
                "location": location,
            }
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "doc1_id": self.doc1.get("document_id"),
            "doc2_id": self.doc2.get("document_id"),
            "total_changes": len(self.changes),
            "changes": self.changes,
            "summary": self.generate_summary(),
        }

    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        if not self.changes:
            return "No changes detected between documents."

        summary_parts = []
        change_types = {}

        for change in self.changes:
            ctype = change["type"]
            change_types[ctype] = change_types.get(ctype, 0) + 1

        for ctype, count in change_types.items():
            summary_parts.append(f"{count} {ctype}")

        return f"Detected {len(self.changes)} total changes: " + ", ".join(
            summary_parts
        )


def compare_documents(doc1: dict, doc2: dict) -> DocumentDiff:
    """
    Compare two regulatory documents and detect changes.

    Args:
        doc1: First document (baseline)
        doc2: Second document (comparison)

    Returns:
        DocumentDiff object containing all detected changes
    """
    diff = DocumentDiff(doc1, doc2)

    # Compare text content
    _compare_text(doc1, doc2, diff)

    # Compare entities (obligations, thresholds, jurisdictions)
    if "entities" in doc1 and "entities" in doc2:
        _compare_entities(doc1["entities"], doc2["entities"], diff)

    return diff


def _compare_text(doc1: dict, doc2: dict, diff: DocumentDiff):
    """Compare document text and detect changes"""
    text1 = doc1.get("text", "")
    text2 = doc2.get("text", "")

    if text1 == text2:
        return

    # Use difflib to find differences
    matcher = difflib.SequenceMatcher(None, text1, text2)
    similarity = matcher.ratio()

    if similarity < 1.0:
        diff.add_change(
            "text_modified",
            f"Document text changed ({similarity*100:.1f}% similar)",
            old_value=len(text1),
            new_value=len(text2),
        )

    # Find specific text blocks that changed
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "delete":
            diff.add_change(
                "text_removed",
                "Text section removed",
                old_value=text1[i1:i2][:100],  # First 100 chars
                location=f"chars {i1}-{i2}",
            )
        elif tag == "insert":
            diff.add_change(
                "text_added",
                "Text section added",
                new_value=text2[j1:j2][:100],  # First 100 chars
                location=f"chars {j1}-{j2}",
            )
        elif tag == "replace":
            diff.add_change(
                "text_replaced",
                "Text section modified",
                old_value=text1[i1:i2][:100],
                new_value=text2[j1:j2][:100],
                location=f"chars {i1}-{i2}",
            )


def _compare_entities(entities1: list, entities2: list, diff: DocumentDiff):
    """Compare extracted entities and detect changes"""

    # Group entities by type
    entities1_by_type = _group_entities_by_type(entities1)
    entities2_by_type = _group_entities_by_type(entities2)

    all_types = set(entities1_by_type.keys()) | set(entities2_by_type.keys())

    for entity_type in all_types:
        e1 = entities1_by_type.get(entity_type, [])
        e2 = entities2_by_type.get(entity_type, [])

        # Compare obligations
        if entity_type == "OBLIGATION":
            _compare_obligations(e1, e2, diff)

        # Compare thresholds
        elif entity_type == "THRESHOLD":
            _compare_thresholds(e1, e2, diff)

        # Compare jurisdictions
        elif entity_type == "JURISDICTION":
            _compare_jurisdictions(e1, e2, diff)


def _group_entities_by_type(entities: list) -> dict:
    """Group entities by their type"""
    grouped = {}
    for entity in entities:
        entity_type = entity.get("type", "UNKNOWN")
        if entity_type not in grouped:
            grouped[entity_type] = []
        grouped[entity_type].append(entity)
    return grouped


def _compare_obligations(obs1: list, obs2: list, diff: DocumentDiff):
    """Compare obligations between documents"""

    # Create text-based sets for comparison
    texts1 = {_normalize_text(ob.get("text", "")) for ob in obs1}
    texts2 = {_normalize_text(ob.get("text", "")) for ob in obs2}

    # Find added obligations
    added = texts2 - texts1
    for text in added:
        diff.add_change(
            "obligation_added",
            "New obligation detected",
            new_value=text[:200],
        )

    # Find removed obligations
    removed = texts1 - texts2
    for text in removed:
        diff.add_change(
            "obligation_removed",
            "Obligation removed",
            old_value=text[:200],
        )

    # Find modified obligations (similar text but not exact match)
    for ob1 in obs1:
        text1 = _normalize_text(ob1.get("text", ""))
        for ob2 in obs2:
            text2 = _normalize_text(ob2.get("text", ""))
            similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
            if 0.7 < similarity < 1.0:  # Similar but not identical
                diff.add_change(
                    "obligation_modified",
                    f"Obligation modified ({similarity*100:.1f}% similar)",
                    old_value=text1[:200],
                    new_value=text2[:200],
                )


def _compare_thresholds(thresholds1: list, thresholds2: list, diff: DocumentDiff):
    """Compare thresholds between documents"""

    # Create threshold dictionaries for comparison
    t1_values = _extract_threshold_values(thresholds1)
    t2_values = _extract_threshold_values(thresholds2)

    # Find all unique keys
    all_keys = set(t1_values.keys()) | set(t2_values.keys())

    for key in all_keys:
        val1 = t1_values.get(key)
        val2 = t2_values.get(key)

        if val1 is None and val2 is not None:
            diff.add_change(
                "threshold_added",
                f"New threshold: {key}",
                new_value=val2,
            )
        elif val1 is not None and val2 is None:
            diff.add_change(
                "threshold_removed",
                f"Threshold removed: {key}",
                old_value=val1,
            )
        elif val1 != val2:
            # Calculate percent change if both are numeric
            try:
                v1 = float(val1)
                v2 = float(val2)
                pct_change = ((v2 - v1) / v1) * 100 if v1 != 0 else float("inf")
                diff.add_change(
                    "threshold_changed",
                    f"Threshold changed: {key} ({pct_change:+.1f}%)",
                    old_value=val1,
                    new_value=val2,
                )
            except (ValueError, TypeError):
                diff.add_change(
                    "threshold_changed",
                    f"Threshold changed: {key}",
                    old_value=val1,
                    new_value=val2,
                )


def _extract_threshold_values(thresholds: list) -> dict:
    """Extract threshold values as a dictionary"""
    result = {}
    for threshold in thresholds:
        attrs = threshold.get("attrs", {})
        value = attrs.get("value")
        unit = attrs.get("unit_normalized", attrs.get("unit"))
        if value is not None:
            key = f"{attrs.get('concept', 'unknown')}_{unit or 'units'}"
            result[key] = value
    return result


def _compare_jurisdictions(jurisdictions1: list, jurisdictions2: list, diff: DocumentDiff):
    """Compare jurisdictions between documents"""

    # Extract jurisdiction names
    names1 = {j.get("attrs", {}).get("name") for j in jurisdictions1 if j.get("attrs")}
    names2 = {j.get("attrs", {}).get("name") for j in jurisdictions2 if j.get("attrs")}

    # Find differences
    added = names2 - names1
    removed = names1 - names2

    for name in added:
        diff.add_change(
            "jurisdiction_added",
            f"New jurisdiction mentioned: {name}",
            new_value=name,
        )

    for name in removed:
        diff.add_change(
            "jurisdiction_removed",
            f"Jurisdiction no longer mentioned: {name}",
            old_value=name,
        )


def _normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, remove extra whitespace)"""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()
