"""
data_cleaning.py
================
Day 2 Steps 1-3 — Clean nav_history, investor_transactions, scheme_performance
and copy all 10 cleaned CSVs to data/processed/

Run:
    python data_cleaning.py
"""

import os
import pandas as pd

RAW_DIR       = "data/raw"
PROCESSED_DIR = "data/processed"
REPORT_PATH   = "reports/cleaning_report_day2.txt"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs("reports", exist_ok=True)

LOG = []
def log(msg):
    print(msg)
    LOG.append(msg)


# =============================================================
# STEP 1 — nav_history.csv
# =============================================================
def clean_nav_history():
    log("\n" + "="*60)
    log("  STEP 1 — Cleaning nav_history")
    log("="*60)

    df = pd.read_csv(os.path.join(RAW_DIR, "02_nav_history.csv"), low_memory=False)
    log(f"  Loaded        : {len(df):,} rows")

    # 1a. Parse dates
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    bad = df["date"].isna().sum()
    if bad:
        df.dropna(subset=["date"], inplace=True)
        log(f"  Dropped bad dates : {bad}")
    else:
        log("  [OK] All dates parsed successfully")

    # 1b. Sort
    df.sort_values(["amfi_code", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    log("  [OK] Sorted by amfi_code + date")

    # 1c. Remove duplicates
    dups = df.duplicated(subset=["amfi_code", "date"]).sum()
    df.drop_duplicates(subset=["amfi_code", "date"], keep="first", inplace=True)
    log(f"  [OK] Duplicates removed : {dups}")

    # 1d. Validate NAV > 0
    invalid = (df["nav"] <= 0).sum()
    df = df[df["nav"] > 0]
    log(f"  [OK] NAV <= 0 removed   : {invalid}")

    # 1e. Forward-fill gaps (weekends/holidays)
    original = len(df)
    all_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    frames = []
    for code, grp in df.groupby("amfi_code"):
        grp = grp.set_index("date").reindex(all_dates)
        grp["amfi_code"] = code
        grp["nav"] = grp["nav"].ffill()
        grp = grp.dropna(subset=["nav"])
        grp = grp.reset_index().rename(columns={"index": "date"})
        frames.append(grp)
    df = pd.concat(frames, ignore_index=True)[["amfi_code", "date", "nav"]]
    log(f"  [OK] Forward-filled     : {len(df)-original:,} gap rows added")
    log(f"  Final shape             : {df.shape[0]:,} rows x {df.shape[1]} cols")
    log(f"  NAV range               : {df['nav'].min():.4f} to {df['nav'].max():.4f}")
    log(f"  Date range              : {df['date'].min().date()} to {df['date'].max().date()}")

    df.to_csv(os.path.join(PROCESSED_DIR, "02_nav_history.csv"), index=False)
    log(f"  Saved -> data/processed/02_nav_history.csv")
    return df


# =============================================================
# STEP 2 — investor_transactions.csv
# =============================================================
def clean_investor_transactions():
    log("\n" + "="*60)
    log("  STEP 2 — Cleaning investor_transactions")
    log("="*60)

    df = pd.read_csv(os.path.join(RAW_DIR, "08_investor_transactions.csv"), low_memory=False)
    log(f"  Loaded        : {len(df):,} rows")

    # 2a. Parse dates
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], format="%Y-%m-%d", errors="coerce")
    bad = df["transaction_date"].isna().sum()
    if bad:
        df.dropna(subset=["transaction_date"], inplace=True)
        log(f"  Dropped bad dates : {bad}")
    else:
        log("  [OK] All dates parsed successfully")

    # 2b. Standardise transaction_type
    type_map = {
        "sip":        "SIP",
        "lumpsum":    "Lumpsum",
        "lump sum":   "Lumpsum",
        "lump-sum":   "Lumpsum",
        "redemption": "Redemption",
        "redeem":     "Redemption",
    }
    df["transaction_type"] = df["transaction_type"].str.strip()
    df["transaction_type"] = df["transaction_type"].apply(
        lambda x: type_map.get(str(x).lower(), x)
    )
    log(f"  [OK] transaction_type   : {df['transaction_type'].value_counts().to_dict()}")

    # 2c. Validate amount > 0
    invalid = (df["amount_inr"] <= 0).sum()
    df = df[df["amount_inr"] > 0]
    log(f"  [OK] amount <= 0 removed: {invalid}")

    # 2d. KYC status check
    VALID_KYC = {"Verified", "Pending", "Rejected"}
    df["kyc_status"] = df["kyc_status"].str.strip()
    bad_kyc = (~df["kyc_status"].isin(VALID_KYC)).sum()
    log(f"  [OK] KYC status values  : {df['kyc_status'].value_counts().to_dict()}")
    if bad_kyc:
        log(f"  [WARN] Invalid KYC rows : {bad_kyc}")

    # 2e. Strip all string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    log(f"  Final shape             : {df.shape[0]:,} rows x {df.shape[1]} cols")

    df.to_csv(os.path.join(PROCESSED_DIR, "08_investor_transactions.csv"), index=False)
    log(f"  Saved -> data/processed/08_investor_transactions.csv")
    return df


# =============================================================
# STEP 3 — scheme_performance.csv
# =============================================================
def clean_scheme_performance():
    log("\n" + "="*60)
    log("  STEP 3 — Cleaning scheme_performance")
    log("="*60)

    df = pd.read_csv(os.path.join(RAW_DIR, "07_scheme_performance.csv"), low_memory=False)
    log(f"  Loaded        : {len(df):,} rows")

    # 3a. Ensure return columns are numeric
    return_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct"]
    for col in return_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        log(f"  [OK] {col:<28} range: {df[col].min():.2f}% to {df[col].max():.2f}%")

    # 3b. Validate expense_ratio_pct 0.1% - 2.5%
    df["expense_ratio_pct"] = pd.to_numeric(df["expense_ratio_pct"], errors="coerce")
    out_of_range = df[(df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)]
    if out_of_range.empty:
        log(f"  [OK] expense_ratio_pct  all within 0.1%-2.5% "
            f"(range: {df['expense_ratio_pct'].min():.2f}%-{df['expense_ratio_pct'].max():.2f}%)")
    else:
        log(f"  [WARN] expense_ratio out of range: {len(out_of_range)} rows")
        df["expense_ratio_flag"] = (df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)

    # 3c. Flag anomalies
    df["beats_benchmark"] = df["alpha"] > 0
    df["alpha_flag"]      = df["alpha"] < -3.0
    df["drawdown_flag"]   = df["max_drawdown_pct"] < -30.0
    df["neg_5yr_flag"]    = df["return_5yr_pct"] < 0

    log(f"  [OK] Beats benchmark    : {df['beats_benchmark'].sum()} / {len(df)} funds")
    log(f"  [OK] Alpha < -3 flag    : {df['alpha_flag'].sum()} funds")
    log(f"  [OK] Drawdown > 30% flag: {df['drawdown_flag'].sum()} funds")
    log(f"  [OK] Negative 5yr flag  : {df['neg_5yr_flag'].sum()} funds")
    log(f"  Final shape             : {df.shape[0]:,} rows x {df.shape[1]} cols")

    df.to_csv(os.path.join(PROCESSED_DIR, "07_scheme_performance.csv"), index=False)
    log(f"  Saved -> data/processed/07_scheme_performance.csv")
    return df


# =============================================================
# STEP 4 — Copy + date-parse remaining 7 CSVs
# =============================================================
def clean_remaining():
    log("\n" + "="*60)
    log("  STEP 4 — Processing remaining 7 datasets")
    log("="*60)

    configs = {
        "01_fund_master.csv":          ["launch_date"],
        "03_aum_by_fund_house.csv":    ["date"],
        "04_monthly_sip_inflows.csv":  ["month"],
        "05_category_inflows.csv":     ["month"],
        "06_industry_folio_count.csv": ["month"],
        "09_portfolio_holdings.csv":   ["portfolio_date"],
        "10_benchmark_indices.csv":    ["date"],
    }

    for fname, date_cols in configs.items():
        src = os.path.join(RAW_DIR, fname)
        if not os.path.exists(src):
            log(f"  [SKIP] Not found: {src}")
            continue
        df = pd.read_csv(src, low_memory=False)
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()
        df.to_csv(os.path.join(PROCESSED_DIR, fname), index=False)
        log(f"  [OK] {fname:<40} {len(df):>6} rows saved")


# =============================================================
# MAIN
# =============================================================
if __name__ == "__main__":
    print("Starting Day 2 data cleaning ...\n")
    nav  = clean_nav_history()
    txn  = clean_investor_transactions()
    perf = clean_scheme_performance()
    clean_remaining()

    # Write report
    with open(REPORT_PATH, "w") as f:
        f.write("DATA CLEANING REPORT - Day 2\n")
        f.write("="*60 + "\n\n")
        f.write("\n".join(LOG))
    print(f"\nCleaning report saved -> {REPORT_PATH}")

    print("\n" + "="*60)
    print("  Day 2 cleaning COMPLETE")
    print(f"  nav_history        : {len(nav):,} rows")
    print(f"  investor_txn       : {len(txn):,} rows")
    print(f"  scheme_performance : {len(perf):,} rows")
    print("  All 10 CSVs        -> data/processed/")
    print("="*60)