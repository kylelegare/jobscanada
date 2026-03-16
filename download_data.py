"""
Download and process Canadian wage data from Open Canada.

Downloads the 2025 wages CSV, filters to national-level data,
and creates occupations.csv by merging with occupations.json.

Usage:
    python download_data.py
"""

import csv
import io
import json
import re
import httpx

# 2025 wages CSV from Open Canada portal
WAGES_URL = "https://open.canada.ca/data/dataset/adad580f-76b0-4502-bd05-20c125de9116/resource/9da94d63-b178-4a64-aeb3-b6a3bd721ad2/download/2a71-das-wage2025opendata-esdc-all-19nov2025-vf.csv"


def main():
    # Load occupations
    with open("occupations.json") as f:
        occupations = json.load(f)

    occ_by_code = {o["code"]: o for o in occupations}
    print(f"Loaded {len(occupations)} occupations")

    # Download wages CSV
    print("Downloading wages CSV...")
    r = httpx.get(WAGES_URL, follow_redirects=True, verify=False, timeout=120)
    r.raise_for_status()
    print(f"Downloaded {len(r.content)} bytes")

    # Parse CSV
    # Try to detect encoding
    text = r.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    # Filter to national level and map to our occupations
    wages = {}
    for row in reader:
        noc_raw = row.get("NOC_CNP", "").strip()
        # Extract 5-digit code from formats like "NOC_21232" or just "21232"
        m = re.search(r"(\d{5})", noc_raw)
        if not m:
            continue
        code = m.group(1)

        # Filter to national level
        prov = row.get("prov", "").strip()
        er_code = row.get("ER_Code_Code_RE", "").strip()
        if prov not in ("NAT", "") or (er_code and er_code not in ("ER00", "")):
            # Also try checking if it's national by other means
            if "Canada" not in row.get("ER_Name", ""):
                continue

        if code not in occ_by_code:
            continue

        median = row.get("Median_Wage_Salaire_Median", "").strip()
        low = row.get("Low_Wage_Salaire_Minium", "").strip()
        high = row.get("High_Wage_Salaire_Maximal", "").strip()
        annual_flag = row.get("Annual_Wage_Flag_Salaire_annuel", "").strip()

        try:
            median_val = float(median) if median else None
            low_val = float(low) if low else None
            high_val = float(high) if high else None
            is_annual = annual_flag == "1"
        except ValueError:
            continue

        # Convert hourly to annual (assume 2080 hours/year)
        if median_val and not is_annual:
            annual_pay = int(median_val * 2080)
            hourly_pay = median_val
        elif median_val and is_annual:
            annual_pay = int(median_val)
            hourly_pay = round(median_val / 2080, 2)
        else:
            annual_pay = None
            hourly_pay = None

        wages[code] = {
            "median_hourly": hourly_pay,
            "median_annual": annual_pay,
            "low_hourly": low_val if not is_annual else (round(low_val / 2080, 2) if low_val else None),
            "high_hourly": high_val if not is_annual else (round(high_val / 2080, 2) if high_val else None),
        }

    print(f"Matched wages for {len(wages)} of {len(occupations)} occupations")

    # Write occupations.csv
    with open("occupations.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "code", "slug", "title", "category", "category_code", "teer",
            "teer_desc", "median_pay_annual", "median_pay_hourly",
            "low_pay_hourly", "high_pay_hourly",
        ])
        writer.writeheader()

        matched = 0
        for occ in occupations:
            code = occ["code"]
            wage = wages.get(code, {})
            writer.writerow({
                "code": code,
                "slug": occ["slug"],
                "title": occ["title"],
                "category": occ["category"],
                "category_code": occ["category_code"],
                "teer": occ["teer"],
                "teer_desc": occ["teer_desc"],
                "median_pay_annual": wage.get("median_annual", ""),
                "median_pay_hourly": wage.get("median_hourly", ""),
                "low_pay_hourly": wage.get("low_hourly", ""),
                "high_pay_hourly": wage.get("high_hourly", ""),
            })
            if wage:
                matched += 1

    print(f"Wrote occupations.csv with {len(occupations)} rows ({matched} with wage data)")


if __name__ == "__main__":
    main()
