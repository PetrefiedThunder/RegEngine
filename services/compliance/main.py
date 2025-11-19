#!/usr/bin/env python3
"""
RegEngine Compliance API Service

REST API for multi-industry compliance checklist validation.
Returns yes/no pass/fail status with line-item checklists.
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum

from checklist_engine import (
    ComplianceChecklistEngine,
    ChecklistResult,
    ValidationStatus,
)
from fsma_engine import FSMA204ComplianceEngine

# Import shared authentication
import sys
sys.path.append("/home/user/RegEngine")
from shared.auth import require_api_key, APIKey


app = FastAPI(
    title="RegEngine Compliance API",
    description="Multi-industry compliance checklist validation",
    version="1.0.0",
)

# Initialize checklist engine
engine = ComplianceChecklistEngine(plugin_directory="/home/user/RegEngine/industry_plugins")
fsma_engine = FSMA204ComplianceEngine()


# ============================================================================
# Request/Response Models
# ============================================================================

class ChecklistListResponse(BaseModel):
    """List of available compliance checklists"""
    checklists: List[Dict[str, Any]]
    total: int


class ValidationRequest(BaseModel):
    """Request to validate compliance against a checklist"""
    checklist_id: str = Field(..., description="ID of the compliance checklist")
    customer_config: Dict[str, Any] = Field(
        ...,
        description="Customer configuration/answers keyed by requirement ID",
        example={
            "hipaa_001": True,
            "hipaa_002": True,
            "hipaa_003": False,
        }
    )


class ValidationItemResponse(BaseModel):
    """Validation result for a single checklist item"""
    requirement_id: str
    requirement: str
    regulation: str
    status: str  # PASS, FAIL, WARNING, NOT_APPLICABLE
    evidence: Optional[str] = None
    remediation: Optional[str] = None


class ValidationResponse(BaseModel):
    """Complete validation result"""
    checklist_id: str
    checklist_name: str
    industry: str
    jurisdiction: str
    overall_status: str  # PASS, FAIL, WARNING
    pass_rate: float = Field(..., description="Pass rate as decimal (0.0-1.0)")
    items: List[ValidationItemResponse]
    next_steps: List[str]


class TraceabilityPlanModel(BaseModel):
    plan_document: Optional[str] = None
    plan_owner: Optional[str] = None
    update_frequency_months: Optional[int] = None
    training_program: Optional[str] = None
    product_scope: List[str] = Field(default_factory=list)
    digital_workflow: Optional[bool] = None
    kpi_dashboard: Optional[bool] = None


class KDECaptureModel(BaseModel):
    receiving: List[str] = Field(default_factory=list)
    transformation: List[str] = Field(default_factory=list)
    shipping: List[str] = Field(default_factory=list)
    cooling: List[str] = Field(default_factory=list)


class RecordkeepingModel(BaseModel):
    retention_years: Optional[int] = None
    retrieval_time_hours: Optional[int] = None
    digital_system: bool = False
    storage_format: Optional[str] = None
    system_of_record: Optional[str] = None


class TechnologyModel(BaseModel):
    capabilities: List[str] = Field(default_factory=list)
    integration_notes: Optional[str] = None


class FSMAAssessmentRequest(BaseModel):
    """FSMA 204 facility profile input"""

    facility_name: str = Field(..., description="Facility under evaluation")
    facility_type: Optional[str] = Field(None, description="e.g., RTE salads, seafood processor")
    products: List[str] = Field(default_factory=list)
    traceability_plan: TraceabilityPlanModel = Field(default_factory=TraceabilityPlanModel)
    kde_capture: KDECaptureModel = Field(default_factory=KDECaptureModel)
    critical_tracking_events: List[str] = Field(default_factory=list)
    recordkeeping: RecordkeepingModel = Field(default_factory=RecordkeepingModel)
    technology: TechnologyModel = Field(default_factory=TechnologyModel)


class DimensionScoreModel(BaseModel):
    id: str
    name: str
    weight: float
    score: float
    status: str
    rationale: str
    gaps: List[str]


class FSMAAssessmentResponse(BaseModel):
    rule_name: str
    regulator: str
    effective_date: Optional[str]
    facility_name: str
    overall_score: float
    risk_level: str
    dimension_scores: List[DimensionScoreModel]
    remediation_actions: List[str]


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance",
        "version": "1.0.0",
        "checklists_loaded": len(engine.checklists),
    }


@app.get("/checklists", response_model=ChecklistListResponse)
def list_checklists(
    industry: Optional[str] = None,
    api_key: APIKey = Depends(require_api_key),
):
    """
    List all available compliance checklists

    - **industry**: Optional filter by industry (e.g., "finance", "healthcare")

    Returns list of checklists with metadata (ID, name, industry, jurisdiction)
    """
    checklists = engine.list_checklists(industry=industry)
    return ChecklistListResponse(checklists=checklists, total=len(checklists))


@app.get("/checklists/{checklist_id}")
def get_checklist(
    checklist_id: str,
    api_key: APIKey = Depends(require_api_key),
):
    """
    Get full details of a specific compliance checklist

    - **checklist_id**: Checklist identifier (e.g., "hipaa_compliance", "capital_requirements")

    Returns full checklist definition including all items and validation rules
    """
    checklist = engine.get_checklist(checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail=f"Checklist not found: {checklist_id}")
    return checklist


@app.post("/validate", response_model=ValidationResponse)
def validate_compliance(
    request: ValidationRequest,
    api_key: APIKey = Depends(require_api_key),
):
    """
    Validate customer configuration against a compliance checklist

    **Returns yes/no pass/fail status with line-item results**

    Request body:
    ```json
    {
      "checklist_id": "hipaa_compliance",
      "customer_config": {
        "hipaa_001": true,
        "hipaa_002": true,
        "hipaa_003": false
      }
    }
    ```

    Response:
    ```json
    {
      "overall_status": "FAIL",
      "pass_rate": 0.67,
      "items": [
        {
          "requirement_id": "hipaa_001",
          "requirement": "Encrypt PHI at rest",
          "status": "PASS",
          "evidence": "Requirement met"
        },
        {
          "requirement_id": "hipaa_003",
          "requirement": "Role-Based Access Control",
          "status": "FAIL",
          "evidence": "Requirement not met",
          "remediation": "Implement RBAC system..."
        }
      ],
      "next_steps": [
        "Address failed requirements before launching",
        "→ Implement RBAC for PHI access"
      ]
    }
    ```
    """
    try:
        result = engine.validate_checklist(
            checklist_id=request.checklist_id,
            customer_config=request.customer_config
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert to response model
    return ValidationResponse(
        checklist_id=result.checklist_id,
        checklist_name=result.checklist_name,
        industry=result.industry,
        jurisdiction=result.jurisdiction,
        overall_status=result.overall_status.value,
        pass_rate=result.pass_rate,
        items=[
            ValidationItemResponse(
                requirement_id=item.requirement_id,
                requirement=item.requirement,
                regulation=item.regulation,
                status=item.status.value,
                evidence=item.evidence,
                remediation=item.remediation,
            )
            for item in result.items
        ],
        next_steps=result.next_steps,
    )


@app.get("/industries")
def list_industries(api_key: APIKey = Depends(require_api_key)):
    """
    List all supported industries

    Returns: List of industry names with checklist counts
    """
    industries = {}
    for checklist in engine.checklists.values():
        industry = checklist.get("industry", "unknown")
        industries[industry] = industries.get(industry, 0) + 1

    return {
        "industries": [
            {"name": name, "checklist_count": count}
            for name, count in sorted(industries.items())
        ],
        "total": len(industries),
    }


@app.post("/fsma-204/assess", response_model=FSMAAssessmentResponse)
def assess_fsma_readiness(
    request: FSMAAssessmentRequest,
    api_key: APIKey = Depends(require_api_key),
):
    """Run a FSMA 204 readiness assessment"""

    profile = request.dict()
    report = fsma_engine.evaluate(profile)
    payload = report.to_dict()
    metadata = payload.get("rule_metadata", {})

    return FSMAAssessmentResponse(
        rule_name=metadata.get("rule_name", "FSMA 204"),
        regulator=metadata.get("regulator", "FDA"),
        effective_date=metadata.get("effective_date"),
        facility_name=payload.get("facility_name", request.facility_name),
        overall_score=payload.get("overall_score", 0.0),
        risk_level=payload.get("risk_level", "UNKNOWN"),
        dimension_scores=[DimensionScoreModel(**item) for item in payload.get("dimension_scores", [])],
        remediation_actions=payload.get("remediation_actions", []),
    )


# ============================================================================
# Example Usage (for documentation)
# ============================================================================

@app.get("/examples/hipaa")
def example_hipaa_validation():
    """
    Example: HIPAA compliance validation

    Shows sample request/response for healthcare compliance check
    """
    return {
        "description": "Example HIPAA compliance check",
        "request": {
            "checklist_id": "hipaa_compliance",
            "customer_config": {
                "hipaa_001": True,
                "hipaa_002": True,
                "hipaa_003": True,
                "hipaa_004": False,  # FAIL
                "hipaa_005": True,
                "hipaa_006": False,  # FAIL
                "hipaa_007": True,
                "hipaa_008": True,
            }
        },
        "expected_response": {
            "overall_status": "WARNING",
            "pass_rate": 0.75,
            "items_failed": 2,
            "next_steps": [
                "Address 2 failed requirements",
                "→ Enable audit logging for PHI access",
                "→ Document breach notification process for 500+ affected individuals"
            ]
        }
    }


@app.get("/examples/finance")
def example_finance_validation():
    """
    Example: Finance capital requirements validation

    Shows sample request/response for financial compliance check
    """
    return {
        "description": "Example finance capital requirements check",
        "request": {
            "checklist_id": "capital_requirements",
            "customer_config": {
                "cap_001": 500000,  # $500k net capital
                "cap_002": 7.5,     # 7.5% Tier 1 ratio
                "cap_003": 95.0,    # 95% LCR (FAIL)
            }
        },
        "expected_response": {
            "overall_status": "WARNING",
            "pass_rate": 0.67,
            "items_failed": 1,
            "next_steps": [
                "Address 1 failed requirement",
                "→ Increase high-quality liquid assets to meet 100% LCR minimum"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
