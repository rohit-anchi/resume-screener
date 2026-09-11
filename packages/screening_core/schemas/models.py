"""Versioned application schemas derived from knowledge/model/screening-ontology.md."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.0.0"


class Versioned(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION


# ---------------------------------------------------------------- enums
class RequirementCategory(str, Enum):
    eligibility = "eligibility"
    required_experience = "required_experience"
    preferred_experience = "preferred_experience"
    skill = "skill"
    qualification = "qualification"
    certification = "certification"
    domain_knowledge = "domain_knowledge"
    leadership = "leadership"
    delivery = "delivery"
    communication = "communication"
    stakeholder_management = "stakeholder_management"
    technical_knowledge = "technical_knowledge"
    location_or_work_arrangement = "location_or_work_arrangement"
    work_authorisation = "work_authorisation"
    travel = "travel"
    other = "other"


class Importance(str, Enum):
    eligibility = "eligibility"
    required = "required"
    preferred = "preferred"
    contextual = "contextual"
    unscorable = "unscorable"


class MatchStatus(str, Enum):
    confirmed = "confirmed"
    strong = "strong"
    partial = "partial"
    weak = "weak"
    no_evidence_located = "no_evidence_located"
    contradictory = "contradictory"
    not_assessable = "not_assessable"
    human_review_required = "human_review_required"


class MatchType(str, Enum):
    direct = "direct"
    equivalent_term = "equivalent_term"
    transferable = "transferable"
    none = "none"


class EligibilityStatus(str, Enum):
    meets_declared_eligibility = "meets_declared_eligibility"
    does_not_meet_declared_eligibility = "does_not_meet_declared_eligibility"
    additional_information_required = "additional_information_required"
    not_evaluated = "not_evaluated"
    human_review_required = "human_review_required"


class EvidenceType(str, Enum):
    employment_role = "employment_role"
    employment_achievement = "employment_achievement"
    skill_mention = "skill_mention"
    education = "education"
    certification = "certification"
    summary_statement = "summary_statement"
    explicit_statement_of_absence = "explicit_statement_of_absence"


class Mode(str, Enum):
    candidate = "candidate"
    recruiter_assist = "recruiter_assist"
    evaluation = "evaluation"


class HumanAction(str, Enum):
    move_forward = "move_forward"
    hold_for_review = "hold_for_review"
    request_additional_information = "request_additional_information"
    decline_with_human_reason = "decline_with_human_reason"


# ---------------------------------------------------------------- shared
class SourceLocation(Versioned):
    document_id: str
    section: Optional[str] = None
    page: Optional[int] = None
    char_start: int
    char_end: int
    text_span: str


class Period(Versioned):
    start: Optional[str] = Field(None, description="YYYY-MM or None if unknown")
    end: Optional[str] = Field(None, description="YYYY-MM, 'present', or None")
    start_uncertain: bool = False
    end_uncertain: bool = False


# ---------------------------------------------------------------- documents
class DocumentFinding(Versioned):
    code: str
    severity: Literal["info", "warning", "critical"]
    message: str
    location: Optional[SourceLocation] = None


class IngestedDocument(Versioned):
    document_id: str
    kind: Literal["resume", "job_description"]
    filename: str
    media_type: str
    sha256: str
    byte_size: int
    page_count: Optional[int] = None
    extracted_text: str
    redacted_text: str = ""
    accepted: bool
    findings: list[DocumentFinding] = []
    parser_version: str


class ParseabilityReport(Versioned):
    document_id: str
    text_extraction_success: bool
    image_only_content: bool
    ocr_required: bool
    ocr_available: bool = False
    name_extracted: bool
    contact_fields_extracted: bool
    employment_history_extracted: bool
    dates_extracted: bool
    education_extracted: bool
    certifications_extracted: bool
    section_order_clear: bool
    table_or_column_interference: bool
    chronology_conflicts: int
    missing_dates: int
    duplicate_content: bool
    injection_suspected: bool
    hidden_text_suspected: bool
    parseability_score: float = Field(ge=0, le=100)
    notes: list[str] = []


# ---------------------------------------------------------------- job
class Threshold(Versioned):
    value: float
    unit: Literal["years", "months", "count"]
    comparator: Literal[">=", ">", "<=", "==", "<"] = ">="


class Requirement(Versioned):
    requirement_id: str
    text: str
    normalised_concept: str
    alternative_concepts: list[str] = Field(default_factory=list, description="OR-alternatives when the requirement says 'X or Y'")
    category: RequirementCategory
    importance: Importance
    evidence_type: str
    minimum_threshold: Optional[Threshold] = None
    source_location: SourceLocation
    confidence: float = Field(ge=0, le=1)
    human_review_required: bool = False
    review_reason: Optional[str] = None
    extraction_method: Literal["rule", "lexicon", "llm_proposed_validated", "human"] = "rule"
    weight: float = 1.0


class ApplicationAnswer(Versioned):
    question_id: str
    question_text: str
    answer: Any


class EligibilityRule(Versioned):
    rule_id: str
    question_id: str
    description: str
    operator: Literal["equals", "not_equals", "in", "gte", "lte", "truthy"]
    expected: Any
    legal_basis: str = Field(description="Employer-declared job-related basis; required for auditability")


class Job(Versioned):
    job_id: str
    title: str
    document: IngestedDocument
    requirements: list[Requirement] = []
    eligibility_rules: list[EligibilityRule] = []
    requirements_version: int = 1


# ---------------------------------------------------------------- candidate
class Evidence(Versioned):
    evidence_id: str
    candidate_id: str
    evidence_type: EvidenceType
    normalised_concepts: list[str]
    source_location: SourceLocation
    employer: Optional[str] = None
    role: Optional[str] = None
    employment_period: Optional[Period] = None
    quantified: bool = False
    inferred: bool = False
    confidence: float = Field(ge=0, le=1)


class Candidate(Versioned):
    candidate_id: str
    document: IngestedDocument
    evidence: list[Evidence] = []
    parseability: Optional[ParseabilityReport] = None
    contradictions: list[str] = []
    application_answers: list[ApplicationAnswer] = []


# ---------------------------------------------------------------- matching
class Match(Versioned):
    match_id: str
    requirement_id: str
    evidence_ids: list[str]
    match_status: MatchStatus
    match_type: MatchType
    coverage: float = Field(ge=0, le=1)
    evidence_strength: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reason: str
    verification_question: Optional[str] = None
    human_review_required: bool = False
    computed_duration_months: Optional[int] = None


# ---------------------------------------------------------------- eligibility
class EligibilityFinding(Versioned):
    rule_id: str
    status: EligibilityStatus
    explanation: str
    answer_used: Any = None


class EligibilityResult(Versioned):
    status: EligibilityStatus
    findings: list[EligibilityFinding]
    uses_resume_inference: Literal[False] = False


# ---------------------------------------------------------------- scoring
class Contribution(Versioned):
    requirement_id: str
    match_id: str
    points_available: float
    points_awarded: float
    explanation: str


class ComponentScore(Versioned):
    component: str
    weight_percent: float
    raw_score: float = Field(ge=0, le=100)
    weighted_points: float
    contributions: list[Contribution] = []
    excluded_requirement_ids: list[str] = []
    explanation: str


class RubricConfig(Versioned):
    rubric_id: str
    rubric_version: str
    weights: dict[str, float]
    confidence_review_threshold: float = 0.6
    near_threshold_tolerance_months: int = 6
    rubric_hash: str = ""

    @model_validator(mode="after")
    def _weights_sum(self) -> "RubricConfig":
        total = round(sum(self.weights.values()), 6)
        if total != 100.0:
            raise ValueError(f"rubric weights must total 100, got {total}")
        return self


class ScoreResult(Versioned):
    alignment_index: float = Field(ge=0, le=100)
    band_label: str
    band_caveat: str
    components: list[ComponentScore]
    overall_confidence: float = Field(ge=0, le=1)
    rubric_id: str
    rubric_version: str
    rubric_hash: str
    qualification_scoring_suppressed: bool = False
    suppression_reason: Optional[str] = None


# ---------------------------------------------------------------- profiles
class Scenario(Versioned):
    scenario_id: str
    title: str
    description: str
    delivery_label: Literal["DOCUMENTED", "CONFIGURATION-DEPENDENT", "OPTIONAL", "THIRD-PARTY", "COMMON PRACTICE", "UNVERIFIED"]
    claim_ids: list[str]
    emphasis: list[str] = []


class PlatformProfile(Versioned):
    profile_id: str
    display_name: str
    platform: Optional[str]
    disclaimer: str
    emphasis: list[str]
    scenarios: list[Scenario]
    report_sections_emphasised: list[str] = []


# ---------------------------------------------------------------- screening
class ScreeningRequest(Versioned):
    job_id: str
    candidate_id: str
    screening_profile: str = "platform_neutral"
    rubric_id: str = "default"
    mode: Mode = Mode.candidate
    application_answers: list[ApplicationAnswer] = []
    employer_rules: list[EligibilityRule] = []
    requested_outputs: list[str] = ["alignment_report", "parseability_report", "evidence_map", "platform_scenarios"]
    initiated_by: str = "anonymous"


class Finding(Versioned):
    requirement_id: str
    requirement_text: str
    importance: Importance
    status: MatchStatus
    candidate_label: str
    evidence_excerpts: list[str]
    locations: list[SourceLocation]
    confidence: float
    explanation: str
    missing_information: Optional[str]
    verification_question: Optional[str]
    score_effect: Optional[str]
    human_review_required: bool


class ScreeningResult(Versioned):
    screening_id: str
    request: ScreeningRequest
    job_title: str
    requirements: list[Requirement]
    evidence: list[Evidence]
    matches: list[Match]
    eligibility: EligibilityResult
    score: ScoreResult
    parseability: ParseabilityReport
    findings: list[Finding]
    scenarios: list[Scenario]
    profile: PlatformProfile
    recommended_human_action: HumanAction
    review_triggers: list[str]
    document_findings: list[DocumentFinding]
    versions: dict[str, str]
    limitations: list[str]
    created_at: str


# ---------------------------------------------------------------- audit
class AuditEvent(Versioned):
    event_id: str
    event_type: str
    timestamp: str
    screening_id: Optional[str]
    actor: str
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str = ""


class ReviewAction(Versioned):
    screening_id: str
    actor: str
    actor_role: str
    action: Literal["accept_finding", "reject_finding", "edit_requirement", "link_evidence", "change_match_status", "mark_not_assessable", "add_note", "request_candidate_information", "override_score", "escalate_compliance", "record_decision"]
    target_id: Optional[str] = None
    new_value: Any = None
    reason: str = Field(min_length=3)
    human_decision: Optional[HumanAction] = None
