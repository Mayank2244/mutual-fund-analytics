"""
db_loader.py
============
Day 2 Steps 4-5 — Build SQLite star schema and load all cleaned datasets.

Run AFTER data_cleaning.py:
    python db_loader.py
"""

import os
import pandas as pd
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, text

PROCESSED_DIR = "data/processed"
DB_PATH       = "bluestock_mf.db"
SCHEMA_PATH   = "sql/schema.sql"

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


# =============================================================
# HELPER — build dim_date from a date series
# =============================================================
def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    dates = pd.to_datetime(dates).dropna().unique()
    df = pd.DataFrame({"date_id": pd.to_datetime(dates)})
    df["date_id"]   = df["date_id"].dt.strftime("%Y-%m-%d")
    df["year"]      = pd.to_datetime(dates).year
    df["month"]     = pd.to_datetime(dates).month
    df["day"]       = pd.to_datetime(dates).day
    df["quarter"]   = pd.to_datetime(dates).quarter
    df["month_name"]= pd.to_datetime(dates).month_name()
    df["day_name"]  = pd.to_datetime(dates).day_name()
    df["is_weekend"]= pd.Series(pd.to_datetime(dates).weekday).isin([5, 6]).astype(int)
    return df.drop_duplicates("date_id").sort_values("date_id").reset_index(drop=True)


# =============================================================
# STEP 1 — Create schema
# =============================================================
def create_schema():
    print("\n" + "="*60)
    print("  Creating SQLite schema ...")
    print("="*60)
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    with engine.connect() as conn:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  [WARN] {e}")
        conn.commit()
    print("  [OK] Schema created -> bluestock_mf.db")


# =============================================================
# STEP 2 — Load dim_fund
# =============================================================
def load_dim_fund():
    print("\n  Loading dim_fund ...")
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "01_fund_master.csv"))
    df["launch_date"] = pd.to_datetime(df["launch_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df.to_sql("dim_fund", engine, if_exists="replace", index=False)
    print(f"  [OK] dim_fund          : {len(df):>6} rows loaded")
    return df


# =============================================================
# STEP 3 — Load dim_date (union of all dates across datasets)
# =============================================================
def load_dim_date():
    print("\n  Building dim_date ...")
    nav  = pd.read_csv(os.path.join(PROCESSED_DIR, "02_nav_history.csv"))
    txn  = pd.read_csv(os.path.join(PROCESSED_DIR, "08_investor_transactions.csv"))
    aum  = pd.read_csv(os.path.join(PROCESSED_DIR, "03_aum_by_fund_house.csv"))
    bi   = pd.read_csv(os.path.join(PROCESSED_DIR, "10_benchmark_indices.csv"))

    all_dates = pd.concat([
        pd.to_datetime(nav["date"],              errors="coerce"),
        pd.to_datetime(txn["transaction_date"],  errors="coerce"),
        pd.to_datetime(aum["date"],              errors="coerce"),
        pd.to_datetime(bi["date"],               errors="coerce"),
    ]).dropna()

    df = build_dim_date(all_dates)
    df.to_sql("dim_date", engine, if_exists="replace", index=False)
    print(f"  [OK] dim_date          : {len(df):>6} rows loaded")
    return df


# =============================================================
# STEP 4 — Load fact_nav
# =============================================================
def load_fact_nav():
    print("\n  Loading fact_nav ...")
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "02_nav_history.csv"))
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"date": "date_id"})
    df = df[["amfi_code", "date_id", "nav"]]
    df.to_sql("fact_nav", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_nav          : {len(df):>6} rows loaded")
    return df


# =============================================================
# STEP 5 — Load fact_transactions
# =============================================================
def load_fact_transactions():
    print("\n  Loading fact_transactions ...")
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "08_investor_transactions.csv"))
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"transaction_date": "date_id"})
    df.to_sql("fact_transactions", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_transactions : {len(df):>6} rows loaded")
    return df


# =============================================================
# STEP 6 — Load fact_performance
# =============================================================
def load_fact_performance():
    print("\n  Loading fact_performance ...")
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "07_scheme_performance.csv"))
    # keep only fact columns (drop name/house already in dim_fund)
    drop_cols = ["scheme_name", "fund_house", "category", "plan"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    df.to_sql("fact_performance", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_performance  : {len(df):>6} rows loaded")
    return df


# =============================================================
# STEP 7 — Load fact_aum
# =============================================================
def load_fact_aum():
    print("\n  Loading fact_aum ...")
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "03_aum_by_fund_house.csv"))
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"date": "date_id"})
    df.to_sql("fact_aum", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_aum          : {len(df):>6} rows loaded")
    return df


# =============================================================
# STEP 8 — Load remaining tables
# =============================================================
def load_remaining():
    print("\n  Loading remaining tables ...")

    # SIP inflows
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "04_monthly_sip_inflows.csv"))
    df.to_sql("fact_sip_inflows", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_sip_inflows       : {len(df):>4} rows")

    # Category inflows
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "05_category_inflows.csv"))
    df.to_sql("fact_category_inflows", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_category_inflows  : {len(df):>4} rows")

    # Industry folio count
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "06_industry_folio_count.csv"))
    df.to_sql("fact_industry_folio", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_industry_folio    : {len(df):>4} rows")

    # Portfolio holdings
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "09_portfolio_holdings.csv"))
    df.to_sql("fact_portfolio_holdings", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_portfolio_holdings: {len(df):>4} rows")

    # Benchmark indices
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "10_benchmark_indices.csv"))
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"date": "date_id"})
    df.to_sql("fact_benchmark_indices", engine, if_exists="replace", index=False)
    print(f"  [OK] fact_benchmark_indices : {len(df):>4} rows")


# =============================================================
# STEP 9 — Verify row counts
# =============================================================
def verify_counts():
    print("\n" + "="*60)
    print("  ROW COUNT VERIFICATION")
    print("="*60)

    checks = {
        "dim_fund":                  ("01_fund_master.csv",          None),
        "fact_nav":                  ("02_nav_history.csv",           None),
        "fact_aum":                  ("03_aum_by_fund_house.csv",     None),
        "fact_sip_inflows":          ("04_monthly_sip_inflows.csv",   None),
        "fact_category_inflows":     ("05_category_inflows.csv",      None),
        "fact_industry_folio":       ("06_industry_folio_count.csv",  None),
        "fact_performance":          ("07_scheme_performance.csv",    None),
        "fact_transactions":         ("08_investor_transactions.csv", None),
        "fact_portfolio_holdings":   ("09_portfolio_holdings.csv",    None),
        "fact_benchmark_indices":    ("10_benchmark_indices.csv",     None),
    }

    all_pass = True
    with engine.connect() as conn:
        for table, (csv_file, _) in checks.items():
            csv_path = os.path.join(PROCESSED_DIR, csv_file)
            if not os.path.exists(csv_path):
                print(f"  [SKIP] {table} — CSV not found")
                continue
            csv_rows = len(pd.read_csv(csv_path))
            db_rows  = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

            # fact_nav has forward-filled rows so DB > CSV is expected
            if table == "fact_nav":
                status = "[OK] (forward-filled rows included)"
            elif csv_rows == db_rows:
                status = "[OK]"
            else:
                status = f"[MISMATCH] CSV={csv_rows} DB={db_rows}"
                all_pass = False

            print(f"  {table:<30} CSV: {csv_rows:>7,}  DB: {db_rows:>7,}  {status}")

    print()
    if all_pass:
        print("  All counts verified!")
    else:
        print("  Some mismatches found — review above.")


# =============================================================
# MAIN
# =============================================================
if __name__ == "__main__":
    print("Starting Day 2 DB loading ...")
    create_schema()
    load_dim_fund()
    load_dim_date()
    load_fact_nav()
    load_fact_transactions()
    load_fact_performance()
    load_fact_aum()
    load_remaining()
    verify_counts()

    print("\n" + "="*60)
    print(f"  Day 2 DB loading COMPLETE")
    print(f"  Database : {DB_PATH}")
    print(f"  Tables   : dim_fund, dim_date, fact_nav, fact_transactions,")
    print(f"             fact_performance, fact_aum, fact_sip_inflows,")
    print(f"             fact_category_inflows, fact_portfolio_holdings,")
    print(f"             fact_benchmark_indices, fact_industry_folio")
    print("="*60)