"""
Scrape OaSIS occupation profiles and save as Markdown.

For each of the 516 unit groups, fetches the OaSIS profile page and
extracts: title, also-known-as titles, core competencies, main duties,
employment requirements, and work context summary.

Usage:
    python scrape_profiles.py
    python scrape_profiles.py --start 0 --end 10   # test on first 10
"""

import argparse
import json
import os
import re
import time
import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://noc.esdc.gc.ca/OaSIS/OaSISOccProfile"
PAGES_DIR = "pages"


def fetch_profile(client, oasis_codes, version="2025.0"):
    """Fetch the first available OaSIS profile for a unit group."""
    # Try each OaSIS code in order until one works
    codes_to_try = sorted(oasis_codes) if oasis_codes else []
    for oasis_code in codes_to_try:
        params = {
            "GocTemplateCulture": "en-CA",
            "code": oasis_code,
            "version": version,
        }
        r = client.get(BASE_URL, params=params, follow_redirects=True, timeout=30)
        if r.status_code == 200:
            return r.text
    # If none worked, raise
    raise Exception(f"All OaSIS codes returned errors: {codes_to_try}")


def extract_panel_body(h3_tag):
    """Extract text from the panel-body sibling of an h3's panel-heading parent."""
    heading_div = h3_tag.find_parent("div", class_="panel-heading")
    if heading_div:
        body = heading_div.find_next_sibling("div", class_=re.compile(r"panel-body"))
        if body:
            return body
    # Fallback: look at direct siblings of the h3
    return None


def parse_profile(html, title):
    """Extract key sections from the profile HTML into Markdown."""
    soup = BeautifulSoup(html, "lxml")
    sections = []

    sections.append(f"# {title}\n")

    # Also known as
    aka_h3 = soup.find("h3", string=re.compile(r"Also known as", re.I))
    if aka_h3:
        body = extract_panel_body(aka_h3)
        if body:
            titles = [li.get_text(strip=True) for li in body.find_all("li")]
            if titles:
                sections.append("## Also known as\n")
                sections.append(", ".join(titles) + "\n")

    # Core competencies
    comp_h3 = soup.find("h3", string=re.compile(r"Core competencies", re.I))
    if comp_h3:
        body = extract_panel_body(comp_h3)
        if body:
            text = body.get_text(separator="\n", strip=True)
            if text:
                sections.append("## Core competencies\n")
                sections.append(text + "\n")

    # Main duties
    duties_h3 = soup.find("h3", string=re.compile(r"Main duties", re.I))
    if duties_h3:
        body = extract_panel_body(duties_h3)
        if body:
            duties_ul = body.find("ul")
            if duties_ul:
                sections.append("## Main duties\n")
                for li in duties_ul.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        sections.append(f"- {text}\n")

    # Employment requirements - education section
    edu_h3 = soup.find("h3", string=re.compile(r"Education.*certification", re.I))
    if edu_h3:
        body = extract_panel_body(edu_h3)
        if body:
            items = body.find_all("li")
            paragraphs = body.find_all("p")
            content = []
            for li in items:
                text = li.get_text(strip=True)
                if text:
                    content.append(f"- {text}")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content.append(text)
            if content:
                sections.append("## Employment requirements\n")
                sections.append("\n".join(content) + "\n")

    # Additional info
    add_h3 = soup.find("h3", string=re.compile(r"Additional information", re.I))
    if add_h3:
        body = extract_panel_body(add_h3)
        if body:
            text = body.get_text(separator="\n", strip=True)
            if text:
                sections.append("## Additional information\n")
                sections.append(text + "\n")

    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    os.makedirs(PAGES_DIR, exist_ok=True)

    with open("occupations.json") as f:
        occupations = json.load(f)

    subset = occupations[args.start:args.end]
    print(f"Scraping {len(subset)} occupation profiles...")

    client = httpx.Client(verify=False)
    errors = []
    skipped = 0

    for i, occ in enumerate(subset):
        slug = occ["slug"]
        code = occ["code"]
        md_path = os.path.join(PAGES_DIR, f"{slug}.md")

        if os.path.exists(md_path) and not args.force:
            skipped += 1
            continue

        print(f"  [{i+1}/{len(subset)}] {occ['title']}...", end=" ", flush=True)

        try:
            html = fetch_profile(client, occ.get("oasis_codes", [f"{code}.00"]))
            markdown = parse_profile(html, occ["title"])

            with open(md_path, "w") as f:
                f.write(markdown)

            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append(code)

        if i < len(subset) - 1:
            time.sleep(args.delay)

    client.close()

    total_done = len(subset) - len(errors) - skipped
    print(f"\nDone. Scraped {total_done} new profiles, {skipped} cached, {len(errors)} errors.")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
