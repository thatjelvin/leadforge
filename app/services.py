import re
from dataclasses import dataclass

RISKY_THRESHOLD = 70
VERIFIED_CONFIDENCE = 90
RISKY_CONFIDENCE = 45
INVALID_CONFIDENCE = 0
# Ranked from strongest to weakest pattern likelihood for MVP defaults.
DEFAULT_PATTERN_CONFIDENCE_SCORES = [90, 85, 75, 72, 68, 66, 64, 62, 50, 48]


@dataclass(frozen=True)
class Candidate:
    email: str
    pattern: str
    confidence: int
    status: str


def _sanitize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def _normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    return normalized


def generate_candidates(first_name: str, last_name: str, domain: str) -> list[Candidate]:
    first = _sanitize(first_name)
    last = _sanitize(last_name)
    d = _normalize_domain(domain)
    if not first or not last or not d:
        return []

    patterns: list[tuple[str, str]] = [
        ("firstname.lastname", f"{first}.{last}@{d}"),
        ("firstnamelastname", f"{first}{last}@{d}"),
        ("firstname", f"{first}@{d}"),
        ("flastname", f"{first[0]}{last}@{d}"),
        ("firstnamel", f"{first}{last[0]}@{d}"),
        ("f.lastname", f"{first[0]}.{last}@{d}"),
        ("firstname_lastname", f"{first}_{last}@{d}"),
        ("lastname.firstname", f"{last}.{first}@{d}"),
        ("lastname", f"{last}@{d}"),
        ("lastnameF", f"{last}{first[0]}@{d}"),
    ]
    return [
        Candidate(
            email=email,
            pattern=pattern,
            confidence=score,
            status="risky" if score < RISKY_THRESHOLD else "verified",
        )
        for (pattern, email), score in zip(patterns, DEFAULT_PATTERN_CONFIDENCE_SCORES, strict=True)
    ]


def verify_email(email: str) -> tuple[str, int]:
    if "@" not in email:
        return "invalid", INVALID_CONFIDENCE
    local_part = email.split("@", 1)[0].lower()
    if "invalid" in local_part or "bounce" in local_part:
        return "invalid", INVALID_CONFIDENCE
    if len(local_part) < 3:
        return "risky", RISKY_CONFIDENCE
    return "verified", VERIFIED_CONFIDENCE
