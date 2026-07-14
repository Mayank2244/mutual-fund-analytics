"""
live_nav_fetch.py
=================
Day 1 Steps 3 & 4 — Fetch live NAV history for 6 large-cap schemes
from mfapi.in, save each as a raw CSV, and print a summary table.

Schemes:
  125497  HDFC Top 100 Direct          (Step 3 - single fetch demo)
  119551  SBI Bluechip Direct          (Step 4)
  120503  ICICI Prudential Bluechip    (Step 4)
  118632  Nippon India Large Cap       (Step 4)
  119092  Axis Bluechip Direct         (Step 4)
  120841  Kotak Bluechip Direct        (Step 4)

Run:
    python live_nav_fetch.py
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime

BASE_URL  = "https://api.mfapi.in/mf"
RAW_DIR   = "data/raw"
DELAY_SEC = 0.6

SCHEMES = {
    125497: "HDFC Top 100 Direct Growth",
    119551: "SBI Bluechip Direct Growth",
    120503: "ICICI Prudential Bluechip Direct Growth",
    118632: "Nippon India Large Cap Direct Growth",
    119092: "Axis Bluechip Direct Growth",
    120841: "Kotak Bluechip Direct Growth",
}


def fetch_scheme(amfi_code, scheme_label):
    url = f"{BASE_URL}/{amfi_code}"
    print(f"\n  [{amfi_code}] {scheme_label}")
    print(f"     URL: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"     ERROR: HTTP {e}")
        return None
    except requests.exceptions.ConnectionError:
        print("     ERROR: Connection failed - check internet access.")
        return None
    except requests.exceptions.Timeout:
        print("     ERROR: Request timed out (>15s).")
        return None

    payload = resp.json()
    meta         = payload.get("meta", {})
    fund_house   = meta.get("fund_house", "")
    scheme_type  = meta.get("scheme_type", "")
    scheme_cat   = meta.get("scheme_category", "")
    scheme_name  = meta.get("scheme_name", scheme_label)
    scheme_code  = meta.get("scheme_code", amfi_code)

    print(f"     OK: {scheme_name}")
    print(f"        House    : {fund_house}")
    print(f"        Category : {scheme_cat}  |  Type: {scheme_type}")

    nav_data = payload.get("data", [])
    if not nav_data:
        print("     WARNING: No NAV data returned.")
        return None

    df = pd.DataFrame(nav_data)
    df.columns = df.columns.str.lower().str.strip()
    df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df.dropna(subset=["date", "nav"], inplace=True)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    df.insert(0, "amfi_code",   scheme_code)
    df.insert(1, "scheme_name", scheme_name)
    df.insert(2, "fund_house",  fund_house)
    df.insert(3, "category",    scheme_cat)

    latest = df.iloc[-1]
    print(f"        Latest NAV : Rs {latest['nav']:.4f}  ({latest['date'].date()})")
    print(f"        Records    : {len(df):,} trading days")
    return df


def save_csv(df, amfi_code, scheme_label):
    slug = (scheme_label.lower()
            .replace(" ", "_").replace("/", "_").replace("-", "_"))
    filepath = os.path.join(RAW_DIR, f"live_nav_{amfi_code}_{slug}.csv")
    df.to_csv(filepath, index=False)
    print(f"        SAVED -> {filepath}")
    return filepath


def fetch_all():
    summary_rows = []
    for code, label in SCHEMES.items():
        df = fetch_scheme(code, label)
        if df is not None:
            save_csv(df, code, label)
            latest = df.iloc[-1]
            summary_rows.append({
                "amfi_code":     code,
                "scheme_name":   label,
                "latest_nav":    round(latest["nav"], 4),
                "nav_date":      latest["date"].date(),
                "total_records": len(df),
            })
        time.sleep(DELAY_SEC)
    return pd.DataFrame(summary_rows) if summary_rows else pd.DataFrame()


if __name__ == "__main__":
    os.makedirs(RAW_DIR, exist_ok=True)
    print("Fetching live NAV data from mfapi.in ...")
    print(f"Schemes to fetch : {len(SCHEMES)}")

    summary = fetch_all()

    if summary.empty:
        print("\nNo data retrieved. Check internet connection or mfapi.in status.")
    else:
        print("\n" + "=" * 70)
        print(f"  LIVE NAV SUMMARY  --  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print(summary.to_string(index=False))
        print("=" * 70)
        out = os.path.join(RAW_DIR, "live_nav_summary.csv")
        summary.to_csv(out, index=False)
        print(f"\nSummary saved -> {out}")
        print(f"Done: {len(summary)}/{len(SCHEMES)} schemes fetched.")