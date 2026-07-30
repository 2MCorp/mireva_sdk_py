"""Wire schemas for MIREVA HTTP request/response (no server/ML imports)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class VisitBlock(BaseModel):
    visit_concept_id: int = 9202
    visit_start_date: date
    visit_type: str = "outpatient"


class PatientBlock(BaseModel):
    patient_id: str
    age: int = Field(ge=0, le=150)
    gender_concept_id: int


class DiagnosisItem(BaseModel):
    concept_id: int
    source_code: str | None = None


class DrugItem(BaseModel):
    concept_id: int
    quantity: float = 0.0
    days_supply: int = 0


class ProcedureItem(BaseModel):
    concept_id: int


class ProviderHistoryBlock(BaseModel):
    facility_concept_id: int = 0
    claims_last_30_days: int = 0
    avg_claim_amount: float = 0.0
    rejection_rate: float = 0.0


class MirevaClaimInput(BaseModel):
    """Single OMOP-oriented claim plus histories for inference."""

    claim_id: str
    visit: VisitBlock
    patient: PatientBlock
    diagnoses: list[DiagnosisItem] = Field(default_factory=list, max_length=100)
    drugs: list[DrugItem] = Field(default_factory=list, max_length=200)
    procedures: list[ProcedureItem] = Field(default_factory=list, max_length=100)
    claimed_amount: float = Field(ge=0)
    policy_start_date: date | None = None
    policy_end_date: date | None = None
    patient_deceased_date: date | None = None
    patient_history: list[MirevaClaimInput] = Field(
        default_factory=list,
        max_length=50,
        description="Prior claims; nested history should be empty on history items",
    )
    provider_history: ProviderHistoryBlock | None = None
    provider_id: str | None = None
    raw_duplicate_of: str | None = None


MirevaClaimInput.model_rebuild()


class RuleFired(BaseModel):
    rule_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    detail: str
    source: Literal["hard_rule", "soft_rule"] = "soft_rule"


class HardRulesResult(BaseModel):
    decision: Literal["PASS", "REJECT"]
    rules_fired: list[RuleFired] = Field(default_factory=list)


class SoftRulesResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rules_fired: list[RuleFired] = Field(default_factory=list)
    frequency_score: float = 0.0
    amount_score: float = 0.0
    clinical_score: float = 0.0
    behavioral_score: float = 0.0
    temporal_score: float = 0.0


class ExplanationReason(BaseModel):
    reason_id: str
    source: Literal["hard_rule", "soft_rule", "ai", "ai_attention"] = "soft_rule"
    severity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    title: str
    detail: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ExplanationBlock(BaseModel):
    summary: str = ""
    reasons: list[ExplanationReason] = Field(default_factory=list)
    provider_facing_message: str = ""
    highlighted_history: list[dict[str, Any]] = Field(default_factory=list)


class MirevaPrediction(BaseModel):
    claim_id: str
    final_decision: Literal["APPROVE", "REVIEW", "REJECT"]
    fraud_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    hard_rules: HardRulesResult
    soft_rules: SoftRulesResult
    model_version: str
    processed_at: str = ""
    explanation: ExplanationBlock = Field(default_factory=ExplanationBlock)
    probabilities: list[float] | None = None
    skipped_model: bool = False
