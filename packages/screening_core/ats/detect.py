"""Application-platform (ATS) detection.

The listing source and the application platform are different concepts: a job can be
listed on LinkedIn and accept applications through Lever, Ashby or any other system.

If the detected platform has no approved Phase 1 knowledge profile, the platform-neutral
profile is selected. The nearest known ATS is never substituted.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from ..schemas.jobdoc import AtsDetection, AtsPlatform, AtsSignal

DETECTOR_VERSION = "ats-detect-2.1.0"

# Host patterns are authoritative; text patterns are weaker corroboration.
HOST_PATTERNS: list[tuple[AtsPlatform, re.Pattern[str]]] = [
    (AtsPlatform.greenhouse, re.compile(r"(?:^|\.)(?:boards|job-boards|my)\.greenhouse\.io$|(?:^|\.)greenhouse\.io$|(?:^|\.)grnh\.se$")),
    (AtsPlatform.lever, re.compile(r"(?:^|\.)jobs\.lever\.co$|(?:^|\.)lever\.co$|(?:^|\.)hire\.lever\.co$")),
    (AtsPlatform.ashby, re.compile(r"(?:^|\.)jobs\.ashbyhq\.com$|(?:^|\.)ashbyhq\.com$")),
    (AtsPlatform.workday, re.compile(r"(?:^|\.)myworkdayjobs\.com$|(?:^|\.)myworkdaysite\.com$|(?:^|\.)wd\d+\.myworkdayjobs\.com$|(?:^|\.)workday\.com$")),
    (AtsPlatform.sap_successfactors, re.compile(r"(?:^|\.)successfactors\.(?:com|eu)$|(?:^|\.)jobs\.sap\.com$|(?:^|\.)rmkcdn\.successfactors\.com$")),
]
TEXT_PATTERNS: list[tuple[AtsPlatform, re.Pattern[str]]] = [
    (AtsPlatform.greenhouse, re.compile(r"\bgreenhouse\b", re.I)),
    (AtsPlatform.lever, re.compile(r"\blever\.co\b|\bpowered by lever\b", re.I)),
    (AtsPlatform.ashby, re.compile(r"\bashbyhq\b|\bashby\b", re.I)),
    (AtsPlatform.workday, re.compile(r"\bmyworkdayjobs\b|\bworkday\b", re.I)),
    (AtsPlatform.sap_successfactors, re.compile(r"\bsuccessfactors\b", re.I)),
]
ATS_HINT = re.compile(r"apply|application|job|career", re.I)
LINKEDIN_HOSTS = re.compile(r"(?:^|\.)linkedin\.com$|(?:^|\.)licdn\.com$|(?:^|\.)lnkd\.in$")

# Approved Phase 1 knowledge profiles only.
PROFILE_BY_PLATFORM = {
    AtsPlatform.greenhouse: "greenhouse_informed",
    AtsPlatform.lever: "lever_informed",
    AtsPlatform.workday: "workday_informed",
    AtsPlatform.sap_successfactors: "successfactors_informed",
}
NEUTRAL = "platform_neutral"


def _unwrap(url: str) -> list[str]:
    """Expand LinkedIn safety redirects and nested encodings into candidate URLs."""
    out = [url]
    try:
        parsed = urlparse(url)
    except ValueError:
        return out
    if "/safety/go" in parsed.path or "redirect" in parsed.path:
        qs = parse_qs(parsed.query)
        for key in ("url", "u", "target"):
            for v in qs.get(key, []):
                out.append(unquote(v))
    decoded = unquote(url)
    if decoded != url:
        out.append(decoded)
    # LinkedIn encodes dots as %2E inside the wrapped url
    for u in list(out):
        if "%2E" in u or "%2e" in u:
            out.append(u.replace("%2E", ".").replace("%2e", "."))
    return out


def _platform_for_host(host: str) -> AtsPlatform | None:
    host = host.lower().rstrip(".")
    for platform, rx in HOST_PATTERNS:
        if rx.search(host):
            return platform
    return None


def detect(links: list[str], document_text: str = "", *, responses_off_platform: bool | None = None, listing_source: str = "linkedin") -> AtsDetection:
    signals: list[AtsSignal] = []
    best: tuple[AtsPlatform, str] | None = None
    external_candidates: list[str] = []

    for raw in links:
        for candidate in _unwrap(raw):
            try:
                host = urlparse(candidate).netloc
            except ValueError:
                continue
            if not host:
                continue
            platform = _platform_for_host(host)
            if platform:
                signals.append(AtsSignal(signal_type="application_link", value=candidate, platform=platform, weight=1.0))
                if best is None:
                    best = (platform, candidate)
            elif not LINKEDIN_HOSTS.search(host.lower()) and ATS_HINT.search(candidate):
                external_candidates.append(candidate)

    if best is None and external_candidates:
        # An off-LinkedIn application destination exists but is not a known platform.
        signals.append(AtsSignal(signal_type="application_link", value=external_candidates[0], platform=AtsPlatform.other, weight=0.6))
        best = (AtsPlatform.other, external_candidates[0])

    for platform, rx in TEXT_PATTERNS:
        m = rx.search(document_text)
        if m:
            signals.append(AtsSignal(signal_type="document_text", value=m.group(0), platform=platform, weight=0.3))

    if responses_off_platform is not None:
        signals.append(AtsSignal(signal_type="listing_metadata", value=f"responses_managed_off_platform={responses_off_platform}", platform=AtsPlatform.unknown, weight=0.1))

    if best is not None:
        platform, url = best
        link_conf = 0.95 if platform != AtsPlatform.other else 0.6
        corroborated = any(s.signal_type == "document_text" and s.platform == platform for s in signals)
        confidence = min(1.0, link_conf + (0.03 if corroborated else 0.0))
        app_url: str | None = url
    else:
        text_only = [s for s in signals if s.signal_type == "document_text"]
        if text_only:
            platform, confidence, app_url = text_only[0].platform, 0.35, None
        else:
            platform, confidence, app_url = AtsPlatform.unknown, 0.2, None

    profile = PROFILE_BY_PLATFORM.get(platform)
    if profile:
        reason = f"Approved Phase 1 knowledge profile exists for {platform.value}."
    else:
        profile = NEUTRAL
        if platform in (AtsPlatform.other, AtsPlatform.ashby):
            reason = (f"Application platform detected as {platform.value}, which has no approved Phase 1 knowledge profile. "
                      "Platform-neutral assessment is used; no nearest-known ATS is substituted.")
        else:
            reason = "Application platform could not be determined; platform-neutral assessment is used."
    return AtsDetection(listing_source=listing_source, application_platform=platform, application_url=app_url,
                        confidence=round(confidence, 2), signals=signals, has_approved_knowledge_profile=platform in PROFILE_BY_PLATFORM,
                        selected_profile_id=profile, profile_selection_reason=reason, responses_managed_off_platform=responses_off_platform)
