"""
Build compact JSON for the website by merging CSV stats with AI exposure scores.

Reads occupations.csv (for stats), scores.json (for AI exposure), and
14100416.csv (StatsCan employment by NOC) for employment counts.
Writes site/data.json.

Usage:
    python build_site_data.py
"""

import csv
import json
import os
import re
from collections import defaultdict


def load_employment(path="14100416.csv", year="2024"):
    """Load employment counts from StatsCan Table 14-10-0416-01.

    Returns dict mapping NOC code (string) to employment in thousands.
    Only loads Canada-level, total gender, Employment rows.
    """
    employment = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row["REF_DATE"] == year
                    and row["GEO"] == "Canada"
                    and row["Labour force characteristics"] == "Employment"
                    and row["Gender"] == "Total - Gender"):
                noc_field = row["National Occupational Classification (NOC)"]
                # Extract code from brackets like [211] or [72]
                m = re.search(r'\[(\d+)\]', noc_field)
                if m and ',' not in m.group(0) and '-' not in m.group(0):
                    code = m.group(1)
                    val = row["VALUE"]
                    if val:
                        employment[code] = float(val)  # in thousands
    return employment


def assign_employment(occupations, employment):
    """Distribute StatsCan employment counts to 5-digit NOC occupations.

    StatsCan provides data at 1/2/3-digit level. For each occupation with
    5-digit code like 21101, we try to find the best match:
    - 3-digit (211) → split equally among occupations sharing that prefix
    - 2-digit (21) → split equally
    - 1-digit (2) → split equally
    """
    # Group occupations by their NOC prefix at each level
    by_prefix = {1: defaultdict(list), 2: defaultdict(list), 3: defaultdict(list)}
    for occ in occupations:
        code = occ["code"]
        for n in [1, 2, 3]:
            prefix = code[:n]
            by_prefix[n][prefix].append(occ)

    assigned = {}
    for occ in occupations:
        code = occ["code"]
        slug = occ["slug"]
        emp = None

        # Try 3-digit, then 2-digit, then 1-digit
        for n in [3, 2, 1]:
            prefix = code[:n]
            if prefix in employment:
                siblings = by_prefix[n][prefix]
                emp = employment[prefix] / len(siblings)  # split equally
                break

        # Convert from thousands to actual count
        if emp is not None:
            assigned[slug] = round(emp * 1000)
        else:
            assigned[slug] = None

    return assigned


def main():
    # Load AI exposure scores
    with open("scores.json") as f:
        scores_list = json.load(f)
    scores = {s["slug"]: s for s in scores_list}

    # Load CSV stats
    with open("occupations.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Load employment data
    emp_path = "14100416.csv"
    if os.path.exists(emp_path):
        employment = load_employment(emp_path)
        print(f"Loaded {len(employment)} NOC employment entries from StatsCan")
        emp_counts = assign_employment(rows, employment)
    else:
        print("No StatsCan employment file found, skipping employment counts")
        emp_counts = {}

    # Merge
    data = []
    for row in rows:
        slug = row["slug"]
        score = scores.get(slug, {})
        pay = row.get("median_pay_annual")
        emp = emp_counts.get(slug)
        data.append({
            "title": row["title"],
            "slug": slug,
            "code": row["code"],
            "category": row["category"],
            "category_code": row["category_code"],
            "teer": row["teer"],
            "teer_desc": row["teer_desc"],
            "pay": int(pay) if pay else None,
            "pay_hourly": float(row["median_pay_hourly"]) if row.get("median_pay_hourly") else None,
            "education": row.get("teer_desc", ""),
            "exposure": score.get("exposure"),
            "exposure_rationale": score.get("rationale"),
            "employment": emp,
        })

    os.makedirs("site", exist_ok=True)
    with open("site/data.json", "w") as f:
        json.dump(data, f)

    scored = [d for d in data if d["exposure"] is not None]
    with_emp = [d for d in scored if d.get("employment")]
    print(f"Wrote {len(data)} occupations to site/data.json ({len(scored)} with scores, {len(with_emp)} with employment)")

    if with_emp:
        total_emp = sum(d["employment"] for d in with_emp)
        weighted_exp = sum(d["employment"] * d["exposure"] for d in with_emp) / total_emp
        print(f"Total employment: {total_emp:,.0f}")
        print(f"Employment-weighted avg exposure: {weighted_exp:.1f}")


if __name__ == "__main__":
    main()
