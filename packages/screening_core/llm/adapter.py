"""Provider-agnostic LLM seam (ADR-004/005).

Rules enforced here, not by policy alone:
- Untrusted documents travel only in `untrusted_documents`; they are never
  formatted into the instruction slot.
- Every proposal must be a schema-valid object whose text spans exist verbatim
  in the source document, otherwise it is discarded and recorded.
- Adapters never return scores or decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

PROMPT_REGISTRY_VERSION = "prompts-2.0.0"
PROMPTS = {
    "requirement_split": "Split the job description into atomic candidate requirements. Return JSON only.",
    "evidence_locate": "Locate spans that evidence the requirement. Return JSON with exact spans only.",
    "explanation_draft": "Draft a neutral explanation for the finding using only provided evidence.",
}


@dataclass
class LLMRequest:
    task: str
    instruction: str
    untrusted_documents: dict[str, str]
    schema_name: str


@dataclass
class LLMProposal:
    task: str
    items: list[dict] = field(default_factory=list)
    provider: str = "null"
    model_version: str = "none"
    discarded: int = 0


class LLMAdapter(Protocol):
    def propose(self, request: LLMRequest) -> LLMProposal: ...


class NullLLMAdapter:
    """Deterministic test double: proposes nothing, so deterministic extraction stands alone."""

    provider = "null"
    model_version = "none"

    def propose(self, request: LLMRequest) -> LLMProposal:
        if request.task not in PROMPTS:
            raise ValueError("unknown task")
        return LLMProposal(task=request.task, provider=self.provider, model_version=self.model_version)


def validate_spans(proposal: LLMProposal, source_text: str) -> LLMProposal:
    """Discard any proposed item whose text_span is not verbatim in the source (anti-fabrication)."""
    kept = [i for i in proposal.items if isinstance(i.get("text_span"), str) and i["text_span"] in source_text]
    proposal.discarded += len(proposal.items) - len(kept)
    proposal.items = kept
    return proposal
