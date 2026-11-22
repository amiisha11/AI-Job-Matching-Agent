"""Turn match and saved-job API payloads into dashboard figures.

Every number comes from those payloads. An empty list is a real zero.
A missing list means the request failed and the figure should stay blank.
"""

SCORE_BUCKETS = ("0–20", "21–40", "41–60", "61–80", "81–100")


def score_bucket(score: float) -> str:
    """Place one match score into the dashboard ranges. 20 stays in the first range."""
    value = float(score)
    if value <= 20:
        return "0–20"
    if value <= 40:
        return "21–40"
    if value <= 60:
        return "41–60"
    if value <= 80:
        return "61–80"
    return "81–100"


def score_distribution(matches: list[dict]) -> list[tuple[str, int]]:
    """Count real match scores in each range."""
    counts = {label: 0 for label in SCORE_BUCKETS}
    for match in matches:
        counts[score_bucket(match["total_score"])] += 1
    return [(label, counts[label]) for label in SCORE_BUCKETS]


def skill_breakdown(matches: list[dict]) -> dict[str, int]:
    """Count exact, semantic, and missing skills across the scored jobs."""
    exact = 0
    semantic = 0
    missing = 0
    for match in matches:
        exact += len(match.get("matched_skills") or [])
        semantic += len(match.get("semantic_matches") or [])
        missing += len(match.get("missing_skills") or [])
    return {
        "Exact matches": exact,
        "Semantic matches": semantic,
        "Missing skills": missing,
    }


def skill_shares(breakdown: dict[str, int]) -> list[tuple[str, int, float | None]]:
    """Share of all skill comparisons. An empty total has no percentage."""
    total = sum(int(count) for count in breakdown.values())
    shares = []
    for label, count in breakdown.items():
        count = int(count)
        share = None if total == 0 else (100 * count / total)
        shares.append((label, count, share))
    return shares


def format_share(value: float | None) -> str:
    """One decimal for a real share. A missing total stays blank."""
    if value is None:
        return "—"
    return f"{value:.1f}%"


def average_match_score(matches: list[dict]) -> float | None:
    """Mean total score. An empty result has no average."""
    if not matches:
        return None
    total = sum(float(match["total_score"]) for match in matches)
    return total / len(matches)


def top_matches(matches: list[dict], limit: int = 3) -> list[dict]:
    """Highest scores first. Ties keep the smaller job id first."""
    ranked = sorted(
        matches,
        key=lambda match: (-float(match["total_score"]), int(match["job"]["id"])),
    )
    return ranked[:limit]


def recent_saved(saved_jobs: list[dict], limit: int = 3) -> list[dict]:
    """Keep the API order, which is newest first."""
    return list(saved_jobs)[:limit]


def format_score(value: float) -> str:
    """Show a score with up to two decimals."""
    text = f"{float(value):.2f}"
    return text.rstrip("0").rstrip(".")
