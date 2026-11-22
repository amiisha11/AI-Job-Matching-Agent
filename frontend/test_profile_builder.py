"""Checks for profile dropdown values. These tests do not open the app or the API."""

import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from profile_builder import education_value, include_custom, profile_payload


def test_custom_entry_trims_and_reuses_an_existing_option():
    options, selected, notice = include_custom(["Python", "SQL"], [], "  python ", "skill")
    assert notice == ""
    assert options == ["Python", "SQL"]
    assert selected == ["Python"]

    options, selected, notice = include_custom(options, selected, "Fortran", "skill")
    assert notice == ""
    assert options[-1] == "Fortran"
    assert selected == ["Python", "Fortran"]

    options, selected, notice = include_custom(options, selected, "fortran", "skill")
    assert selected == ["Python", "Fortran"]

    unchanged_options, unchanged_selected, notice = include_custom(options, selected, "   ", "skill")
    assert notice == "Enter a skill to add."
    assert unchanged_options == options
    assert unchanged_selected == selected


def test_education_and_payload_match_the_existing_create_body():
    assert education_value("Not specified", "") == (None, None)
    assert education_value("B.Tech", "") == ("B.Tech", None)
    assert education_value("Other", "  B.A. ") == ("B.A.", None)
    value, error = education_value("Other", " ")
    assert value is None
    assert error

    payload, payload_error = profile_payload(
        "  Ada   Lovelace ",
        " Ada@Example.com ",
        "M.Tech",
        "",
        ["Python", " python ", " "],
        ["Data Analyst"],
        ["Remote"],
        2,
    )
    assert payload_error is None
    assert payload == {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "education": "M.Tech",
        "degree": None,
        "field_of_study": None,
        "specialization": None,
        "institution": None,
        "graduation_year": None,
        "skills": ["Python"],
        "preferred_roles": ["Data Analyst"],
        "preferred_industries": [],
        "preferred_locations": ["Remote"],
        "preferred_countries": [],
        "remote_preference": None,
        "years_experience": 2,
    }

    rejected, message = profile_payload("", "ada@example.com", "BCA", "", [], [], [], 0)
    assert rejected is None
    assert message == "Enter your name."
    rejected, message = profile_payload("Ada", "ada-at-example", "BCA", "", [], [], [], 0)
    assert rejected is None
    assert "email" in message.casefold()
