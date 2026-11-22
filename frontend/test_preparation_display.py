"""Preparation display helpers. They do not call the API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from preparation import limited_skills, progress_lines


def test_skill_chips_leave_the_rest_for_the_details():
    shown, extra = limited_skills([" SQL ", "", "Excel", "Python", "Tableau"])
    assert shown == ["SQL", "Excel", "Python"]
    assert extra == 1


def test_progress_lines_follow_the_api_counts():
    fraction, counts, finished = progress_lines(
        {"completed": 1, "total": 2, "remaining": 1, "percent": 50, "finished": False}
    )
    assert fraction == "1 / 2 tasks"
    assert counts == "1 completed · 1 remaining"
    assert finished is False
    _, _, done = progress_lines(
        {"completed": 2, "total": 2, "remaining": 0, "percent": 100, "finished": True}
    )
    assert done is True
    _, _, empty = progress_lines(
        {"completed": 0, "total": 0, "remaining": 0, "percent": 0, "finished": False}
    )
    assert empty is False
