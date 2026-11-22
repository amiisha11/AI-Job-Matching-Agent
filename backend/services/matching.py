"""Score a job against a candidate.

The result is a fixed formula. This module does not call Gemini or any
other network service, and it does not touch the database.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticMatch:
    """A required skill paired with one related candidate skill."""

    required_skill: str
    candidate_skill: str
    similarity: float


@dataclass(frozen=True)
class MatchScore:
    """Point breakdown for one candidate and one job."""

    total_score: float
    skill_score: float
    role_score: float
    location_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    semantic_matches: list[SemanticMatch] = field(default_factory=list)


def eligible_for_ranking(job) -> bool:
    """True when a job may receive the 70/20/10 score.

    A listing marked unmatchable, or one whose provider did not supply skill
    requirements, is left out of ranked results. The formula itself is unchanged.
    """
    if getattr(job, "is_matchable", True) is False:
        return False
    if getattr(job, "requirements_available", True) is False:
        return False
    return bool(_labels(getattr(job, "required_skills", None)))


def score_job(candidate, job) -> MatchScore:
    """Score one job for one candidate. The maximum total is 100."""
    matched_skills, missing_skills = compare_skills(
        getattr(candidate, "skills", None),
        getattr(job, "required_skills", None),
    )
    if not _labels(getattr(job, "required_skills", None)):
        skill_score = 0.0
    else:
        required_count = len(matched_skills) + len(missing_skills)
        skill_score = round(70 * len(matched_skills) / required_count, 2)

    role_score = 20.0 if text_matches(getattr(job, "title", None), getattr(candidate, "preferred_roles", None)) else 0.0
    location_score = (
        10.0 if text_matches(getattr(job, "location", None), getattr(candidate, "preferred_locations", None)) else 0.0
    )
    total_score = round(skill_score + role_score + location_score, 2)
    return MatchScore(
        total_score=total_score,
        skill_score=skill_score,
        role_score=role_score,
        location_score=location_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )


def compare_skills(candidate_skills, required_skills) -> tuple[list[str], list[str]]:
    """Return required skills the candidate has, then required skills they lack.

    Comparison ignores case and surrounding space. A job with no required
    skills produces two empty lists so the caller can award 0 without dividing
    by zero.
    """
    candidate_keys = {_normalize(skill) for skill in _labels(candidate_skills)}
    matched: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()
    for skill in _labels(required_skills):
        key = _normalize(skill)
        if not key or key in seen:
            continue
        seen.add(key)
        if key in candidate_keys:
            matched.append(skill.strip())
        else:
            missing.append(skill.strip())
    return matched, missing


def text_matches(job_text, preferences) -> bool:
    """True when a preferred value equals the job text or appears inside it.

    "Data Analyst" matches the title "Junior Data Analyst". Comparison ignores
    case and extra space. Blank preferences do not match.
    """
    target = _normalize(job_text or "")
    if not target:
        return False
    for preference in _labels(preferences):
        wanted = _normalize(preference)
        if wanted and (wanted == target or wanted in target):
            return True
    return False


def _labels(values) -> list[str]:
    if not values:
        return []
    return [value for value in values if isinstance(value, str)]


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def skill_texts_for_embedding(candidate, jobs) -> list[str]:
    """Return only skill strings. Names, emails, and descriptions are excluded."""
    texts = list(_labels(getattr(candidate, "skills", None)))
    for job in jobs:
        texts.extend(_labels(getattr(job, "required_skills", None)))
    return texts


def score_with_skill_vectors(candidate, job, vectors, threshold: float = 0.75) -> MatchScore:
    """Score one job, using vectors only for skills that are not exact matches.

    ``vectors`` maps a normalized skill to its embedding. None means the
    embedding service is unavailable, so the original exact score is returned.
    """
    exact_score = score_job(candidate, job)
    if vectors is None:
        return exact_score

    required = _unique_skills(getattr(job, "required_skills", None))
    available = _unique_skills(getattr(candidate, "skills", None))
    if not required:
        return exact_score

    exact_skills: list[str] = []
    unmatched_required: list[str] = []
    for required_skill in required:
        match_index = _exact_index(required_skill, available)
        if match_index is None:
            unmatched_required.append(required_skill)
        else:
            exact_skills.append(required_skill)
            available.pop(match_index)

    weights = [
        [_semantic_weight(required_skill, candidate_skill, vectors, threshold) for candidate_skill in available]
        for required_skill in unmatched_required
    ]
    semantic_matches: list[SemanticMatch] = []
    matched_required: set[int] = set()
    for row, column in maximum_weight_assignment(weights):
        similarity = weights[row][column]
        semantic_matches.append(
            SemanticMatch(
                required_skill=unmatched_required[row],
                candidate_skill=available[column],
                similarity=similarity,
            )
        )
        matched_required.add(row)
    semantic_matches.sort(key=lambda item: unmatched_required.index(item.required_skill))
    missing_skills = [
        skill for index, skill in enumerate(unmatched_required) if index not in matched_required
    ]
    credit = len(exact_skills) + sum(item.similarity for item in semantic_matches)
    skill_score = round(70 * credit / len(required), 2)
    return MatchScore(
        total_score=round(skill_score + exact_score.role_score + exact_score.location_score, 2),
        skill_score=skill_score,
        role_score=exact_score.role_score,
        location_score=exact_score.location_score,
        matched_skills=exact_skills,
        missing_skills=missing_skills,
        semantic_matches=semantic_matches,
    )


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return the cosine similarity of two vectors, from -1 to 1."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def maximum_weight_assignment(weights: list[list[float]]) -> list[tuple[int, int]]:
    """Pair rows and columns so the total weight is maximized.

    Each row and each column is used at most once. Zero-weight cells are not
    returned. The result does not depend on row or column order.
    """
    if not weights or not weights[0]:
        return []
    row_count = len(weights)
    column_count = len(weights[0])
    size = max(row_count, column_count)
    largest = max((value for row in weights for value in row), default=0.0)
    cost = [[largest for _ in range(size)] for _ in range(size)]
    for row in range(row_count):
        for column in range(column_count):
            cost[row][column] = largest - weights[row][column]
    chosen_columns = _hungarian_min(cost)
    pairs = []
    for row, column in enumerate(chosen_columns):
        if row < row_count and column < column_count and weights[row][column] > 0:
            pairs.append((row, column))
    return pairs


def _unique_skills(values) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for skill in _labels(values):
        cleaned = skill.strip()
        key = _normalize(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _exact_index(required_skill: str, candidate_skills: list[str]) -> int | None:
    required_key = _normalize(required_skill)
    for index, candidate_skill in enumerate(candidate_skills):
        if _normalize(candidate_skill) == required_key:
            return index
    return None


def _semantic_weight(required_skill: str, candidate_skill: str, vectors, threshold: float) -> float:
    required_vector = vectors.get(_normalize(required_skill))
    candidate_vector = vectors.get(_normalize(candidate_skill))
    if not required_vector or not candidate_vector:
        return 0.0
    similarity = round(cosine_similarity(required_vector, candidate_vector), 4)
    if similarity < threshold:
        return 0.0
    return similarity


def _hungarian_min(cost: list[list[float]]) -> list[int]:
    """Return column indexes for a minimum-cost one-to-one assignment."""
    size = len(cost)
    row_potential = [0.0] * (size + 1)
    column_potential = [0.0] * (size + 1)
    column_match = [0] * (size + 1)
    way = [0] * (size + 1)
    for row in range(1, size + 1):
        column_match[0] = row
        current_column = 0
        minimum = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[current_column] = True
            current_row = column_match[current_column]
            delta = float("inf")
            next_column = 0
            for column in range(1, size + 1):
                if used[column]:
                    continue
                reduced = cost[current_row - 1][column - 1] - row_potential[current_row] - column_potential[column]
                if reduced < minimum[column]:
                    minimum[column] = reduced
                    way[column] = current_column
                if minimum[column] < delta:
                    delta = minimum[column]
                    next_column = column
            for column in range(size + 1):
                if used[column]:
                    row_potential[column_match[column]] += delta
                    column_potential[column] -= delta
                else:
                    minimum[column] -= delta
            current_column = next_column
            if column_match[current_column] == 0:
                break
        while True:
            previous_column = way[current_column]
            column_match[current_column] = column_match[previous_column]
            current_column = previous_column
            if current_column == 0:
                break
    assignment = [-1] * size
    for column in range(1, size + 1):
        if column_match[column] != 0:
            assignment[column_match[column] - 1] = column - 1
    return assignment
