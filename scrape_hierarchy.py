"""
Scrape the NOC 2021 OaSIS hierarchy to build occupations.json.

Extracts all 516 five-digit unit groups with titles, descriptions,
broad categories, and TEER levels.

Usage:
    python scrape_hierarchy.py
"""

import json
import re
import httpx
from bs4 import BeautifulSoup

URL = "https://noc.esdc.gc.ca/OaSIS/OaSISHierarchy?version=2025.0"

# NOC broad occupational categories (first digit)
BROAD_CATEGORIES = {
    "0": "Legislative and senior management occupations",
    "1": "Business, finance and administration occupations",
    "2": "Natural and applied sciences and related occupations",
    "3": "Health occupations",
    "4": "Occupations in education, law and social, community and government services",
    "5": "Occupations in art, culture, recreation and sport",
    "6": "Sales and service occupations",
    "7": "Trades, transport and equipment operators and related occupations",
    "8": "Natural resources, agriculture and related production occupations",
    "9": "Occupations in manufacturing and utilities",
}

# TEER levels (second digit)
TEER_LEVELS = {
    "0": "Management",
    "1": "University degree",
    "2": "College diploma or apprenticeship",
    "3": "Secondary school or occupation-specific training",
    "4": "On-the-job training",
    "5": "Short work demonstration",
}


def slugify(title):
    """Convert title to URL-friendly slug."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return s[:80]


def main():
    print("Fetching OaSIS hierarchy...")
    r = httpx.get(URL, follow_redirects=True, verify=False, timeout=60)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # Find all 5-digit unit group <details> elements
    details = soup.find_all("details", class_=re.compile(r"nocLI details_\d{5}"))
    print(f"Found {len(details)} unit group elements")

    occupations = []
    for d in details:
        code_span = d.find("span", class_="nocCode")
        title_span = d.find("span", class_="nocTitle")
        desc_p = d.find("p")

        if not (code_span and title_span):
            continue

        code = code_span.get_text(strip=True)
        title = title_span.get_text(strip=True)
        description = desc_p.get_text(strip=True) if desc_p else ""

        # Get OaSIS profile links for this unit group
        profile_links = d.find_all("a", href=re.compile(r"OaSISOccProfile"))
        oasis_codes = []
        for a in profile_links:
            href = a.get("href", "")
            m = re.search(r"code=(\d{5}\.\d{2})", href)
            if m and m.group(1) not in oasis_codes:
                oasis_codes.append(m.group(1))

        broad_cat = code[0]
        teer = code[1]

        occupations.append({
            "code": code,
            "title": title,
            "slug": slugify(title),
            "description": description,
            "category": BROAD_CATEGORIES.get(broad_cat, "Unknown"),
            "category_code": broad_cat,
            "teer": teer,
            "teer_desc": TEER_LEVELS.get(teer, "Unknown"),
            "oasis_codes": oasis_codes,
        })

    # Write output
    with open("occupations.json", "w") as f:
        json.dump(occupations, f, indent=2)

    print(f"\nWrote {len(occupations)} occupations to occupations.json")

    # Summary by category
    print("\nBy broad category:")
    for cat_code in sorted(BROAD_CATEGORIES):
        count = sum(1 for o in occupations if o["category_code"] == cat_code)
        print(f"  {cat_code}: {BROAD_CATEGORIES[cat_code]} ({count})")


if __name__ == "__main__":
    main()
