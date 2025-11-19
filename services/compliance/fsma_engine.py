#!/usr/bin/env python3
"""Domain-specific FSMA 204 compliance engine"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

import statistics
import yaml


class RiskLevel(Enum):
    """Risk tier for FSMA compliance readiness"""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DimensionScore:
    """Score and metadata for a control dimension"""

    id: str
    name: str
    weight: float
    score: float
    status: RiskLevel
    rationale: str
    gaps: List[str] = field(default_factory=list)


@dataclass
class FSMAComplianceReport:
    """Aggregate FSMA 204 compliance output"""

    rule_metadata: Dict[str, Any]
    facility_name: str
    overall_score: float
    risk_level: RiskLevel
    dimension_scores: List[DimensionScore]
    remediation_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serializable representation"""
        return {
            "rule_metadata": self.rule_metadata,
            "facility_name": self.facility_name,
            "overall_score": round(self.overall_score, 3),
            "risk_level": self.risk_level.value,
            "dimension_scores": [
                {
                    "id": d.id,
                    "name": d.name,
                    "weight": d.weight,
                    "score": round(d.score, 3),
                    "status": d.status.value,
                    "rationale": d.rationale,
                    "gaps": d.gaps,
                }
                for d in self.dimension_scores
            ],
            "remediation_actions": self.remediation_actions,
        }


class FSMA204ComplianceEngine:
    """Domain-specific rules engine for FSMA 204"""

    def __init__(self, definition_file: str = "industry_plugins/food_beverage/fsma_204.yaml"):
        definition_path = Path(definition_file)
        if not definition_path.exists():
            raise FileNotFoundError(f"FSMA definition file not found: {definition_file}")

        with open(definition_path, "r") as handle:
            data = yaml.safe_load(handle)

        self.rule_metadata = data.get("metadata", {})
        self.key_data_elements = data.get("key_data_elements", [])
        self.critical_tracking_events = data.get("critical_tracking_events", [])
        self.control_dimensions = data.get("control_dimensions", {})

        # Build quick lookup tables for KDEs per event
        self._kde_lookup: Dict[str, List[str]] = {
            cte["id"]: cte.get("required_kdes", []) for cte in self.critical_tracking_events
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate(self, operation_profile: Dict[str, Any]) -> FSMAComplianceReport:
        """Evaluate a facility profile and return a structured report"""

        dimension_scores = [
            self._evaluate_traceability_plan(operation_profile),
            self._evaluate_kde_capture(operation_profile),
            self._evaluate_cte_coverage(operation_profile),
            self._evaluate_recordkeeping(operation_profile),
            self._evaluate_technology_stack(operation_profile),
        ]

        total_weight = sum(d.weight for d in dimension_scores)
        weighted_sum = sum(d.score * d.weight for d in dimension_scores)
        overall_score = weighted_sum / total_weight if total_weight else 0.0
        risk_level = self._risk_from_score(overall_score)
        remediation = self._build_remediation_plan(dimension_scores)

        return FSMAComplianceReport(
            rule_metadata=self.rule_metadata,
            facility_name=operation_profile.get("facility_name", "Unknown Facility"),
            overall_score=overall_score,
            risk_level=risk_level,
            dimension_scores=dimension_scores,
            remediation_actions=remediation,
        )

    # ------------------------------------------------------------------
    # Dimension evaluators
    # ------------------------------------------------------------------
    def _evaluate_traceability_plan(self, profile: Dict[str, Any]) -> DimensionScore:
        config = self.control_dimensions.get("traceability_plan", {})
        plan = profile.get("traceability_plan", {}) or {}
        required_fields: List[str] = config.get("required_fields", [])
        missing = [field for field in required_fields if not plan.get(field)]
        base_score = 1 - len(missing) / len(required_fields) if required_fields else 0.0
        base_score = max(base_score, 0.0)

        premium_fields = config.get("premium_fields", [])
        if premium_fields:
            premium_hits = sum(1 for field in premium_fields if plan.get(field))
            base_score += 0.1 * (premium_hits / len(premium_fields))

        base_score = min(base_score, 1.0)
        status = self._status_from_dimension_score(base_score)

        rationale = (
            f"{len(required_fields) - len(missing)} of {len(required_fields)} core elements present"
            if required_fields
            else "No traceability plan metadata configured"
        )
        gaps = [f"Add or document '{field}'" for field in missing]

        return DimensionScore(
            id="traceability_plan",
            name=config.get("name", "Traceability Plan"),
            weight=config.get("weight", 0.2),
            score=base_score,
            status=status,
            rationale=rationale,
            gaps=gaps,
        )

    def _evaluate_kde_capture(self, profile: Dict[str, Any]) -> DimensionScore:
        config = self.control_dimensions.get("kde_capture", {})
        kde_capture = profile.get("kde_capture", {}) or {}
        event_requirements: Dict[str, Dict[str, float]] = config.get("event_requirements", {})

        event_scores: List[float] = []
        gaps: List[str] = []
        rationales: List[str] = []

        for event, requirement in event_requirements.items():
            required_kdes = set(self._kde_lookup.get(event, []))
            recorded_kdes = set(kde_capture.get(event, []))
            coverage = (len(recorded_kdes & required_kdes) / len(required_kdes)) if required_kdes else 0.0
            target = requirement.get("minimum_percentage", 1.0)
            normalized_score = min(coverage / target, 1.0) if target else coverage
            event_scores.append(normalized_score)

            rationales.append(
                f"{event}: {len(recorded_kdes & required_kdes)}/{len(required_kdes)} KDEs tracked"
            )
            if coverage < target:
                percentage = int(coverage * 100)
                target_pct = int(target * 100)
                missing_kdes = sorted(required_kdes - recorded_kdes)
                gap = f"{event} coverage at {percentage}% (target {target_pct}%), missing {missing_kdes}"
                gaps.append(gap)

        score = statistics.mean(event_scores) if event_scores else 0.0
        status = self._status_from_dimension_score(score)
        rationale = ", ".join(rationales) if rationales else "No KDE mappings supplied"

        return DimensionScore(
            id="kde_capture",
            name=config.get("name", "Key Data Elements"),
            weight=config.get("weight", 0.25),
            score=score,
            status=status,
            rationale=rationale,
            gaps=gaps,
        )

    def _evaluate_cte_coverage(self, profile: Dict[str, Any]) -> DimensionScore:
        config = self.control_dimensions.get("cte_coverage", {})
        expected_events = set(config.get("expected_events", []))
        provided_events = set(profile.get("critical_tracking_events", []))
        missing = sorted(expected_events - provided_events)
        coverage = 1 - len(missing) / len(expected_events) if expected_events else 0.0
        coverage = max(min(coverage, 1.0), 0.0)
        status = self._status_from_dimension_score(coverage)

        rationale = (
            f"{len(expected_events) - len(missing)} of {len(expected_events)} events mapped"
            if expected_events
            else "No expected events configured"
        )
        gaps = [f"Add process coverage for '{event}' CTE" for event in missing]

        return DimensionScore(
            id="cte_coverage",
            name=config.get("name", "Critical Tracking Events"),
            weight=config.get("weight", 0.2),
            score=coverage,
            status=status,
            rationale=rationale,
            gaps=gaps,
        )

    def _evaluate_recordkeeping(self, profile: Dict[str, Any]) -> DimensionScore:
        config = self.control_dimensions.get("recordkeeping", {})
        recordkeeping = profile.get("recordkeeping", {}) or {}
        retention_years = recordkeeping.get("retention_years", 0)
        retrieval_time = recordkeeping.get("retrieval_time_hours", 999)
        digital_system = recordkeeping.get("digital_system", False)

        retention_score = min(retention_years / config.get("min_retention_years", 1), 1.0)
        retrieval_score = 1.0 if retrieval_time <= config.get("max_retrieval_hours", 24) else 0.4
        digital_score = 1.0 if digital_system else 0.5

        score = statistics.mean([retention_score, retrieval_score, digital_score])
        status = self._status_from_dimension_score(score)
        gaps: List[str] = []

        if retention_years < config.get("min_retention_years", 1):
            gaps.append(
                f"Increase record retention to {config.get('min_retention_years', 1)} years"
            )
        if retrieval_time > config.get("max_retrieval_hours", 24):
            gaps.append(
                f"Improve retrieval SLA to ≤ {config.get('max_retrieval_hours', 24)} hours"
            )
        if not digital_system:
            gaps.append("Digitize traceability records or centralize in system of record")

        rationale = (
            f"Retention: {retention_years} yrs, Retrieval: {retrieval_time} hrs, Digital: {'yes' if digital_system else 'no'}"
        )

        return DimensionScore(
            id="recordkeeping",
            name=config.get("name", "Recordkeeping"),
            weight=config.get("weight", 0.15),
            score=score,
            status=status,
            rationale=rationale,
            gaps=gaps,
        )

    def _evaluate_technology_stack(self, profile: Dict[str, Any]) -> DimensionScore:
        config = self.control_dimensions.get("technology_enablement", {})
        technology = profile.get("technology", {}) or {}
        capabilities = set(technology.get("capabilities", []))
        required = set(config.get("required_capabilities", []))
        bonus = set(config.get("bonus_capabilities", []))

        required_score = (
            len(capabilities & required) / len(required) if required else 0.0
        )
        bonus_score = (
            len(capabilities & bonus) / len(bonus) if bonus else 0.0
        )

        score = min(required_score + 0.1 * bonus_score, 1.0)
        status = self._status_from_dimension_score(score)

        gaps = [f"Implement capability '{cap}'" for cap in sorted(required - capabilities)]
        rationale = f"Capabilities enabled: {sorted(capabilities)}"

        return DimensionScore(
            id="technology_enablement",
            name=config.get("name", "Technology"),
            weight=config.get("weight", 0.15),
            score=score,
            status=status,
            rationale=rationale,
            gaps=gaps,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _status_from_dimension_score(self, score: float) -> RiskLevel:
        if score >= 0.85:
            return RiskLevel.LOW
        if score >= 0.7:
            return RiskLevel.MODERATE
        if score >= 0.5:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    def _risk_from_score(self, score: float) -> RiskLevel:
        return self._status_from_dimension_score(score)

    def _build_remediation_plan(self, dimensions: List[DimensionScore]) -> List[str]:
        gaps: List[str] = []
        for dimension in dimensions:
            for gap in dimension.gaps:
                gaps.append(f"[{dimension.name}] {gap}")
        if not gaps:
            return ["Maintain FSMA 204 controls and schedule quarterly review meetings."]
        return gaps[:10]


if __name__ == "__main__":
    sample_profile = {
        "facility_name": "Sample Fresh Foods Plant",
        "traceability_plan": {
            "plan_document": "s3://traceability/plan.pdf",
            "plan_owner": "Director, Food Safety",
            "update_frequency_months": 12,
            "training_program": "LMS-FSMA",
            "product_scope": ["fresh-cut fruits"],
            "digital_workflow": True,
            "kpi_dashboard": True,
        },
        "kde_capture": {
            "receiving": [
                "lot_code_source",
                "product_description",
                "quantity_uom",
                "location_identifier",
            ],
            "shipping": [
                "lot_code_source",
                "product_description",
                "quantity_uom",
                "location_identifier",
            ],
            "transformation": ["linked_lot_code", "quantity_uom", "product_description"],
        },
        "critical_tracking_events": ["receiving", "shipping", "transformation"],
        "recordkeeping": {
            "retention_years": 2,
            "retrieval_time_hours": 18,
            "digital_system": True,
        },
        "technology": {
            "capabilities": [
                "serialization",
                "api_access",
                "data_validation_rules",
                "audit_log_export",
                "streaming_events",
            ]
        },
    }

    engine = FSMA204ComplianceEngine()
    report = engine.evaluate(sample_profile)
    print(report.to_dict())
