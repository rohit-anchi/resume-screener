"""Schemas for LinkedIn job-document ingestion, ATS detection and the two-input assessment.

Separate module so Phase 2 core models stay stable; re-exported from schemas.models.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "2.1.0"


class Versioned(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION


# ------------------------------------------------------------------ content classification
class BlockCategory(str, Enum):
    """Classification of every extracted content block.

    `allowed()` members are employer job content; only `requirement_bearing()` members
    may enter requirement extraction and scoring.
    """

    # employer job content
    job_header = "job_header"
    employer_about = "employer_about"
    employer_role_overview = "employer_role_overview"
    employer_team = "employer_team"
    employer_responsibilities = "employer_responsibilities"
    employer_requirements = "employer_requirements"
    employer_preferred = "employer_preferred"
    employer_work_arrangement = "employer_work_arrangement"
    employer_eligibility = "employer_eligibility"
    employer_compensation = "employer_compensation"
    employer_process = "employer_process"
    employer_application_instructions = "employer_application_instructions"
    employer_eeo = "employer_eeo"
    employer_ai_disclosure = "employer_ai_disclosure"
    # LinkedIn-generated / excluded
    linkedin_nav = "linkedin_nav"
    linkedin_job_match = "linkedin_job_match"
    linkedin_applicant_stats = "linkedin_applicant_stats"
    linkedin_candidate_seniority_stats = "linkedin_candidate_seniority_stats"
    linkedin_candidate_education_stats = "linkedin_candidate_education_stats"
    linkedin_premium_insights = "linkedin_premium_insights"
    linkedin_company_insights = "linkedin_company_insights"
    linkedin_similar_jobs = "linkedin_similar_jobs"
    linkedin_advertisement = "linkedin_advertisement"
    linkedin_resume_promotion = "linkedin_resume_promotion"
    linkedin_people_suggestions = "linkedin_people_suggestions"
    page_header_footer = "page_header_footer"
    garbled_fragment = "garbled_fragment"
    unknown = "unknown"

    @classmethod
    def allowed(cls) -> set["BlockCategory"]:
        return {cls.job_header, cls.employer_about, cls.employer_role_overview, cls.employer_team, cls.employer_responsibilities,
                cls.employer_requirements, cls.employer_preferred, cls.employer_work_arrangement, cls.employer_eligibility,
                cls.employer_compensation, cls.employer_process, cls.employer_application_instructions, cls.employer_eeo,
                cls.employer_ai_disclosure}

    @classmethod
    def requirement_bearing(cls) -> set["BlockCategory"]:
        """Only these may produce scored requirements (compensation, EEO, process and AI disclosure are retained but never scored)."""
        return {cls.employer_role_overview, cls.employer_team, cls.employer_responsibilities, cls.employer_requirements,
                cls.employer_preferred, cls.employer_work_arrangement, cls.employer_eligibility}


SECTION_IMPORTANCE = {
    BlockCategory.employer_requirements: "minimum_qualifications",
    BlockCategory.employer_preferred: "preferred_qualifications",
    BlockCategory.employer_responsibilities: "responsibilities",
    BlockCategory.employer_role_overview: "responsibilities",
    BlockCategory.employer_team: "about",
    BlockCategory.employer_work_arrangement: "work_arrangement",
    BlockCategory.employer_eligibility: "eligibility",
}


class ContentBlock(Versioned):
    block_id: str
    page: int
    order: int
    y: float
    x: float
    max_font_size: float
    text: str
    category: BlockCategory
    allowed_for_requirements: bool
    classification_reason: str
    classifier_rule: Optional[str] = None
    review_required: bool = False
    char_start: Optional[int] = Field(None, description="Offset in employer_text when included")
    char_end: Optional[int] = None


class JobSection(Versioned):
    name: str
    category: BlockCategory
    char_start: int
    char_end: int
    block_ids: list[str]


# ------------------------------------------------------------------ ATS detection
class AtsPlatform(str, Enum):
    greenhouse = "greenhouse"
    lever = "lever"
    workday = "workday"
    sap_successfactors = "sap_successfactors"
    ashby = "ashby"
    other = "other"
    unknown = "unknown"


class AtsSignal(Versioned):
    signal_type: Literal["application_link", "document_text", "listing_metadata"]
    value: str
    platform: AtsPlatform
    page: Optional[int] = None
    weight: float = 1.0


class AtsDetection(Versioned):
    listing_source: str = "linkedin"
    application_platform: AtsPlatform
    application_url: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    signals: list[AtsSignal] = []
    has_approved_knowledge_profile: bool
    selected_profile_id: str
    profile_selection_reason: str
    responses_managed_off_platform: Optional[bool] = None


# ------------------------------------------------------------------ job document
class JobDocument(Versioned):
    job_document_id: str
    source_document_id: str
    filename: str
    sha256: str
    page_count: int
    listing_source: str
    employer: Optional[str]
    role_title: Optional[str]
    location: Optional[str]
    employment_type: Optional[str]
    workplace_type: Optional[str]
    compensation_text: Optional[str] = None
    employer_text: str
    blocks: list[ContentBlock]
    sections: list[JobSection]
    excluded_block_ids: list[str]
    excluded_categories: dict[str, int] = {}
    ats: AtsDetection
    extraction_warnings: list[str] = []
    parser_version: str
    classifier_version: str


# ------------------------------------------------------------------ recommendations
class RecommendationKind(str, Enum):
    critical_application_gap = "critical_application_gap"
    make_evidence_explicit = "make_evidence_explicit"
    section_ordering = "section_ordering"
    targeted_summary = "targeted_summary"
    terminology_alignment = "terminology_alignment"
    quantify_achievement = "quantify_achievement"
    skill_needs_context = "skill_needs_context"
    reduce_or_remove = "reduce_or_remove"
    application_field_care = "application_field_care"


class RecommendedEdit(Versioned):
    original_text: Optional[str]
    proposed_text: str
    job_requirement_addressed: Optional[str]
    candidate_evidence_supporting: list[str]
    verification_required: str


class Recommendation(Versioned):
    recommendation_id: str
    kind: RecommendationKind
    priority: Literal["critical", "high", "medium", "low"]
    title: str
    rationale: str
    requirement_ids: list[str] = []
    evidence_ids: list[str] = []
    edit: Optional[RecommendedEdit] = None
    fabrication_guard: str = "Only include this if it is true and you can evidence it in an interview."


# ------------------------------------------------------------------ questions
class QuestionAudience(str, Enum):
    recruiter_screen = "recruiter_screen"
    hiring_manager = "hiring_manager"
    evidence_verification = "evidence_verification"
    seniority_and_scope = "seniority_and_scope"
    gap_focused = "gap_focused"
    employer_and_domain = "employer_and_domain"


class InterviewQuestion(Versioned):
    question_id: str
    audience: QuestionAudience
    question: str
    why_likely: str
    requirement_id: Optional[str]
    requirement_text: Optional[str]
    trigger: str
    trigger_kind: Literal["evidence", "gap", "ambiguity", "scope", "domain", "eligibility"]
    suggested_answer_structure: list[str]
    follow_ups: list[str] = []
    note: str = "Prepare your own answer from real experience. No answer content is generated for you."


# ------------------------------------------------------------------ assessment
class CriticalGap(Versioned):
    requirement_id: str
    requirement_text: str
    status: str
    why_critical: str
    what_would_resolve_it: str


class Assessment(Versioned):
    assessment_id: str
    created_at: str
    mode: str
    job: JobDocument
    candidate_id: str
    resume_document_id: str
    screening_id: str
    ats: AtsDetection
    profile_id: str
    profile_display_name: str
    eligibility_status: str
    alignment_index: Optional[float]
    band_label: str
    component_scores: dict[str, float]
    evidence_confidence: float
    critical_gaps: list[CriticalGap]
    missing_or_ambiguous: list[str]
    recommendations: list[Recommendation]
    questions: list[InterviewQuestion]
    scenario_ids: list[str]
    versions: dict[str, str]
    limitations: list[str]
    audit_event_ids: list[str] = []


# ------------------------------------------------------------------ multi-job module
class MultiJobEntry(Versioned):
    job_document_id: str
    employer: Optional[str]
    role_title: Optional[str]
    application_platform: str
    alignment_index: Optional[float]
    band_label: str
    eligibility_status: str
    required_coverage: float
    critical_gap_count: int
    tailoring_effort: Literal["low", "medium", "high"]
    tailoring_reason: str


class MultiJobReview(Versioned):
    review_id: str
    created_at: str
    candidate_id: str
    entries: list[MultiJobEntry]
    common_requirements: list[str]
    recurring_gaps: list[str]
    domain_fit: dict[str, str]
    seniority_fit: dict[str, str]
    suggested_priority: list[str]
    master_resume_improvements: list[str]
    caveat: str = ("Ranking reflects documented suitability against each job's stated requirements in the submitted documents. "
                   "It is not a hiring probability and does not predict any employer's decision.")


# ------------------------------------------------------------------ profile review module
class ProfileComparisonRow(Versioned):
    dimension: str
    resume_evidence: Optional[str]
    profile_evidence: Optional[str]
    status: Literal["aligned", "missing_in_profile", "missing_in_resume", "potential_contradiction", "not_assessable"]
    explanation: str


class ProfileReview(Versioned):
    review_id: str
    created_at: str
    candidate_id: str
    profile_document_id: str
    resume_document_id: str
    authorisation_confirmed: bool
    rows: list[ProfileComparisonRow]
    missing_profile_evidence: list[str]
    missing_resume_evidence: list[str]
    potential_contradictions: list[str]
    target_market_recommendations: list[str]
    limitations: list[str]
