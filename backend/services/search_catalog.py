"""Role and country settings for live job discovery.

Change this file to add a market or a role. The Adzuna client does not
contain this list. Near-duplicate keywords such as "Python Programmer"
are left out; the same provider listing is removed after the searches.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleSearch:
    """One search phrase and the group it belongs to."""

    category: str
    query: str


ROLE_SEARCHES: tuple[RoleSearch, ...] = (
    RoleSearch("Software development", "Software Engineer"),
    RoleSearch("Software development", "Python Developer"),
    RoleSearch("Software development", "Java Developer"),
    RoleSearch("Software development", "Frontend Developer"),
    RoleSearch("Software development", "Backend Developer"),
    RoleSearch("Software development", "Full Stack Developer"),
    RoleSearch("Data and AI", "Data Analyst"),
    RoleSearch("Data and AI", "Data Scientist"),
    RoleSearch("Data and AI", "AI Engineer"),
    RoleSearch("Data and AI", "Machine Learning Engineer"),
    RoleSearch("Cloud and infrastructure", "DevOps Engineer"),
    RoleSearch("Cloud and infrastructure", "Cloud Engineer"),
    RoleSearch("Internships and entry-level", "Software Engineer Intern"),
    RoleSearch("Internships and entry-level", "Data Analyst Intern"),
    RoleSearch("Internships and entry-level", "AI/ML Intern"),
    RoleSearch("Internships and entry-level", "Graduate Software Engineer"),
)

# Adzuna country codes. Add another code here when a new market is verified.
COUNTRY_NAMES = {
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "in": "India",
    "us": "United States",
    "au": "Australia",
    "ca": "Canada",
    "de": "Germany",
    "fr": "France",
    "nl": "Netherlands",
    "br": "Brazil",
    "za": "South Africa",
}
DEFAULT_DISCOVERY_COUNTRIES = ("gb", "in")

# Listings older than this many days are flagged. They are not hidden.
OLD_LISTING_DAYS = 30
