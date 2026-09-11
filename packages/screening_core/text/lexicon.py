"""Visible, versioned concept lexicon used for normalisation and equivalent-term matching.

Every equivalence is explicit and auditable. Extend via config, never by hidden model output.
"""
from __future__ import annotations

import re

LEXICON_VERSION = "lexicon-2.0.0"

# concept -> list of surface forms (lowercase). First form is the canonical label.
CONCEPTS: dict[str, list[str]] = {
    "product_management": ["product management", "product manager", "product owner", "pm", "product lead", "head of product", "product roadmap", "commercial product experience", "product experience"],
    "roadmap_ownership": ["roadmap", "capability roadmap", "product roadmap", "portfolio roadmap"],
    "stakeholder_management": ["stakeholder management", "stakeholder", "stakeholders", "executive alignment", "cross-functional alignment"],
    "cross_functional_collaboration": ["cross-functional", "cross functional", "collaborated with engineering", "partnered with", "worked with engineering and design"],
    "cloud_platforms": ["cloud platform", "cloud platforms", "aws", "amazon web services", "azure", "gcp", "google cloud", "cloud-native", "cloud"],
    "data_pipelines": ["data pipeline", "data pipelines", "etl", "streaming", "kafka", "telemetry pipeline", "ingestion pipeline"],
    "telemetry": ["telemetry", "observability", "monitoring data", "usage data", "metering"],
    "saas_subscription": ["saas", "xaas", "subscription", "subscription models", "consumption-based", "usage-based billing", "metering and rating"],
    "agile_delivery": ["agile", "scrum", "safe", "sprint", "backlog", "kanban"],
    "sql": ["sql", "postgresql", "postgres", "mysql", "t-sql"],
    "python": ["python"],
    "api_design": ["api", "apis", "rest", "restful", "graphql", "openapi"],
    "written_communication": ["prd", "product requirements", "documentation", "written", "specifications", "feature brief", "briefs", "publishing", "communicate it clearly"],
    "customer_discovery": ["customer discovery", "customer interviews", "user research", "voice of customer", "discovery"],
    "decision_making": ["prioritisation", "prioritization", "trade-offs", "tradeoffs", "decision", "decision-making", "investment decisions", "translating complex", "clear outcomes"],
    "delivery_leadership": ["delivered", "launched", "shipped", "led delivery", "program management", "release"],
    "people_leadership": ["managed a team", "led a team", "direct reports", "people manager", "mentored", "line management"],
    "enterprise_b2b": ["enterprise", "b2b", "enterprise customers", "large accounts"],
    "bachelor_degree": ["bachelor", "bachelor's", "bsc", "b.sc", "ba ", "b.a.", "b.e.", "b.tech", "undergraduate degree"],
    "master_degree": ["master", "master's", "msc", "m.sc", "mba", "m.tech", "postgraduate"],
    "pmp_certification": ["pmp", "project management professional"],
    "scrum_certification": ["csm", "cspo", "certified scrum", "scrum certification", "psm", "pspo"],
    "aws_certification": ["aws certified", "aws solutions architect"],
    "security_compliance": ["security", "compliance", "gdpr", "soc 2", "iso 27001", "privacy"],
    "analytics": ["analytics", "kpis", "metrics", "dashboards", "data-driven", "experimentation", "a/b"],
    "hr_technology": ["hris", "ats", "applicant tracking", "recruiting software", "workday", "successfactors", "greenhouse", "lever"],
    "product_strategy": ["product strategy", "product vision", "vision and strategy", "strategic alignment", "set product strategy"],
    "org_alignment": ["align", "aligning", "alignment", "across an organisation", "across an organization", "organisation-wide",
                      "organization-wide", "across products and teams", "joined up across the business", "aligning stakeholders"],
    "multi_market_platform": ["multiple markets", "multiple brands", "customer segments", "many markets", "one market to many",
                              "international", "globally", "around the world", "utility partners", "utilities", "multi-market"],
    "product_practices": ["product practices", "roadmapping", "discovery, delivery", "goal-setting", "rituals", "operating model",
                          "ways of working", "product culture", "product function", "quarterly roadmaps"],
    "ai_enablement": ["ai", "ai-native", "ai enablement", "genai", "generative ai", "llm", "large language model", "agents",
                      "ai harness", "ai harnesses", "model gateway", "gateways", "ai strategy", "ai product"],
    "platform_product_management": ["platform product", "platform products", "platform product management", "developer tools",
                                    "internal platform", "infrastructure", "shared platforms", "shared capabilities", "core product"],
    "ambiguity_tolerance": ["ambiguity", "incomplete information", "evolving technology", "uncertainty"],
    "learning_mindset": ["curiosity", "pragmatism", "resilience", "experiments", "continuous learning"],
    "systems_thinking": ["systems thinking", "think in systems", "joining the dots", "connect work", "systems"],
    "governance": ["governance", "guard rails", "guardrails", "policy", "controls", "risk", "compliance", "safe and efficient"],
    "adoption": ["adoption", "pilot", "rollout", "enablement", "repeatable adoption", "uptake"],
    "exec_reporting": ["reporting into the exec", "executive team", "reporting directly to ceo", "reports to the ceo", "exec"],
    "people_management_of_managers": ["manager-of-managers", "manager of managers", "managing pms", "managing product managers",
                                      "managing the pms", "hiring, coaching", "pm talent", "raising the quality of product management"],
}

# transferable relationships: source concept -> target concept it may partially support (labelled, never silent)
TRANSFERABLE: dict[str, list[str]] = {
    "project_management": ["delivery_leadership", "agile_delivery", "product_management"],
    "delivery_leadership": ["product_management"],
    "telemetry": ["data_pipelines", "analytics"],
    "data_pipelines": ["cloud_platforms"],
    "saas_subscription": ["enterprise_b2b"],
    "scrum_certification": ["agile_delivery"],
    "pmp_certification": ["delivery_leadership"],
    "people_management_of_managers": ["people_leadership"],
    "stakeholder_management": ["org_alignment"],
    "cross_functional_collaboration": ["org_alignment"],
    "ai_enablement": ["platform_product_management"],
    "people_leadership": ["people_management_of_managers"],
    "platform_product_management": ["product_management"],
    "analytics": ["adoption"],
    "agile_delivery": ["product_practices"],
    "data_pipelines": ["platform_product_management"],
}
CONCEPTS.setdefault("project_management", ["project management", "project manager", "programme management", "program manager"])

_COMPILED: list[tuple[str, re.Pattern[str]]] = []
for concept, forms in CONCEPTS.items():
    for f in sorted(forms, key=len, reverse=True):
        _COMPILED.append((concept, re.compile(r"(?<![\w-])" + re.escape(f.strip()) + r"(?![\w-])", re.I)))


def concepts_in(text: str) -> dict[str, list[tuple[int, int, str]]]:
    """Return concept -> list of (start, end, surface) occurrences."""
    found: dict[str, list[tuple[int, int, str]]] = {}
    for concept, rx in _COMPILED:
        for m in rx.finditer(text):
            found.setdefault(concept, []).append((m.start(), m.end(), m.group(0)))
    return found


def label(concept: str) -> str:
    return CONCEPTS.get(concept, [concept.replace("_", " ")])[0]
