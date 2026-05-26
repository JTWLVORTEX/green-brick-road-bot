"""
Hunter.io API client (replaces Apollo - free tier supports domain search).
Finds founder/owner/CEO contacts at company domains.
"""
import time
import requests
from typing import List, Dict
from src.config import HUNTER_API_KEY

HUNTER_API_BASE = "https://api.hunter.io/v2"

# Titles we consider "founder-equivalent" for podcast guests
FOUNDER_TITLE_KEYWORDS = [
    "founder", "co-founder", "cofounder", "ceo", "chief executive",
    "owner", "president", "managing director", "principal", "managing partner",
]


def _is_founder_title(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in FOUNDER_TITLE_KEYWORDS)


def find_founders_at_domain(domain: str, max_results: int = 3) -> List[Dict]:
    """
    Find founder/owner-level contacts at a company domain via Hunter.io.

    Args:
        domain: Company domain (e.g. "acme.com")
        max_results: Max contacts to return

    Returns:
        List of dicts: name, first_name, last_name, email, title,
        linkedin_url, organization_name
        Returns [] if no founders found or rate limited.
    """
    url = f"{HUNTER_API_BASE}/domain-search"
    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
        "limit": 10,  # fetch up to 10, then filter for founders
        "type": "personal",
    }

    response = requests.get(url, params=params, timeout=15)

    if response.status_code == 429:
        print(f"  Hunter rate limit hit for {domain}, sleeping 5s...")
        time.sleep(5)
        return []
    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()
    emails = data.get("data", {}).get("emails", [])

    results = []
    for person in emails:
        email = person.get("value", "")
        if not email:
            continue
        title = person.get("position", "")
        if not _is_founder_title(title):
            continue
        first = person.get("first_name", "")
        last = person.get("last_name", "")
        results.append({
            "name": f"{first} {last}".strip(),
            "first_name": first,
            "last_name": last,
            "email": email,
            "title": title,
            "linkedin_url": person.get("linkedin", ""),
            "organization_name": data.get("data", {}).get("organization", ""),
        })
        if len(results) >= max_results:
            break

    return results


if __name__ == "__main__":
    # Smoke test: try to find a founder at a well-known domain
    test_domain = "stripe.com"
    print(f"Testing Hunter.io API for founders at {test_domain}...")
    founders = find_founders_at_domain(test_domain, max_results=2)
    print(f"Found {len(founders)} founder-level contacts")
    for f in founders:
        email_masked = f['email'][:3] + "***@" + f['email'].split('@')[1] if '@' in f['email'] else "(no email)"
        print(f"  - {f['name']} | {f['title']} | {email_masked}")
