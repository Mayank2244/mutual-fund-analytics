"""
etl_scheduler.py
================
B1 Bonus — Single-file ETL Scheduler
Auto-fetches live NAV from mfapi.in every weekday at 8:00 PM
Saves raw CSVs + upserts into SQLite database
Logs all activity to logs/etl_scheduler.log

USAGE:
------
1. Run scheduler (keeps running, triggers at 8 PM weekdays):
   python etl_scheduler.py

2. Test immediately (manual trigger):
   python etl_scheduler.py --run-now

3. Setup Windows Task Scheduler (run once as Administrator):
   python etl_scheduler.py --setup-windows

4. Remove Windows Task:
   python etl_scheduler.py --remove-windows

5. View last run summary:
   python etl_scheduler.py --status

6. View run history from DB:
   python etl_scheduler.py --history
"""

import os
import sys
import time
import logging
import subprocess
import requests
import pandas as pd
import schedule
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text

# ─────────────────────────────────────────────────────────────
# CONFIG — edit these if needed
# ─────────────────────────────────────────────────────────────
BASE_URL   = "https://api.mfapi.in/mf"
# DB_PATH    = "bluestock_mf.db"
# RAW_DIR    = Path("data/raw")
# LOG_DIR    = Path("logs")
# LOG_FILE   = LOG_DIR / "etl_scheduler.log"
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "bluestock_mf.db"
RAW_DIR  = BASE_DIR / "data" / "raw"
LOG_DIR  = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "etl_scheduler.log"
RUN_TIME   = "20:00"        # 8:00 PM
DELAY_SEC  = 0.6            # polite delay between API calls
TASK_NAME  = "BluestockETLScheduler"

SCHEMES = {
    125497: "HDFC Top 100 Direct Growth",
    119551: "SBI Bluechip Direct Growth",
    120503: "ICICI Prudential Bluechip Direct Growth",
    118632: "Nippon India Large Cap Direct Growth",
    119092: "Axis Bluechip Direct Growth",
    120841: "Kotak Bluechip Direct Growth",
}

# ─────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("etl_scheduler")


# ═════════════════════════════════════════════════════════════
# SECTION 1 — ETL CORE FUNCTIONS
# ═════════════════════════════════════════════════════════════

def fetch_scheme(amfi_code: int, scheme_name: str) -> pd.DataFrame | None:
    """Fetch NAV history for one scheme from mfapi.in."""
    url = f"{BASE_URL}/{amfi_code}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log.error(f"  [{amfi_code}] Request failed: {exc}")
        return None

    payload  = resp.json()
    nav_data = payload.get("data", [])
    if not nav_data:
        log.warning(f"  [{amfi_code}] No NAV data returned")
        return None

    df = pd.DataFrame(nav_data)
    df.columns = df.columns.str.lower().str.strip()
    df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df.dropna(subset=["date", "nav"], inplace=True)
    df = df[df["nav"] > 0]
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0, "amfi_code",   amfi_code)
    df.insert(1, "scheme_name", scheme_name)

    latest = df.iloc[-1]
    log.info(f"  [{amfi_code}] {scheme_name[:35]:<35} "
             f"NAV: Rs{latest['nav']:.4f}  "
             f"({latest['date'].date()})  "
             f"Records: {len(df):,}")
    return df


def save_raw_csv(df: pd.DataFrame, amfi_code: int,
                 scheme_name: str) -> Path:
    """Save scheme NAV data as raw CSV."""
    slug = (scheme_name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_"))
    path = RAW_DIR / f"live_nav_{amfi_code}_{slug}.csv"
    df.to_csv(path, index=False)
    return path


def upsert_to_db(df: pd.DataFrame, engine) -> int:
    """
    Insert only NEW rows into fact_nav.
    Skips (amfi_code + date) pairs already in the DB.
    Returns count of new rows inserted.
    """
    with engine.connect() as conn:
        try:
            existing = pd.read_sql(
                "SELECT amfi_code, date FROM fact_nav", conn
            )
            existing["date"] = pd.to_datetime(existing["date"])
        except Exception:
            existing = pd.DataFrame(columns=["amfi_code", "date"])

    existing_keys = set(
        zip(existing["amfi_code"].astype(int),
            existing["date"].dt.strftime("%Y-%m-%d"))
    )

    df_new = df.copy()
    df_new["date_str"] = df_new["date"].dt.strftime("%Y-%m-%d")
    df_new = df_new[
        ~df_new.apply(
            lambda r: (int(r["amfi_code"]), r["date_str"])
            in existing_keys, axis=1
        )
    ].drop(columns=["date_str"])

    if df_new.empty:
        return 0

    db_df = df_new[["amfi_code", "date", "nav"]].copy()
    db_df["date"] = db_df["date"].dt.strftime("%Y-%m-%d")
    db_df.to_sql("fact_nav", engine, if_exists="append", index=False)
    return len(db_df)


def log_run_to_db(engine, run_time, schemes_fetched,
                  new_rows, status, error_msg=""):
    """Log each ETL run to etl_run_log table in DB."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS etl_run_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp   TEXT    NOT NULL,
                    schemes_fetched INTEGER,
                    new_nav_rows    INTEGER,
                    status          TEXT,
                    error_msg       TEXT
                )
            """))
            conn.execute(text("""
                INSERT INTO etl_run_log
                    (run_timestamp, schemes_fetched,
                     new_nav_rows, status, error_msg)
                VALUES (:ts, :sf, :nr, :st, :em)
            """), {"ts": run_time, "sf": schemes_fetched,
                   "nr": new_rows, "st": status, "em": error_msg})
            conn.commit()
        except Exception as exc:
            log.error(f"Failed to write run log to DB: {exc}")


# ═════════════════════════════════════════════════════════════
# SECTION 2 — MAIN ETL JOB
# ═════════════════════════════════════════════════════════════

def run_etl_job():
    """Full ETL job: fetch all schemes, save CSVs, upsert DB."""
    run_start = datetime.now()

    # Skip weekends
    if run_start.weekday() >= 5:
        log.info("Today is a weekend — ETL skipped.")
        return

    log.info("=" * 65)
    log.info(f"  ETL JOB STARTED  {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 65)

    # Connect to DB
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        log.info(f"  DB: {DB_PATH}")
    except Exception as exc:
        log.error(f"DB connection failed: {exc}")
        return

    schemes_fetched = 0
    total_new_rows  = 0
    errors          = []
    summary_rows    = []

    for amfi_code, scheme_name in SCHEMES.items():
        try:
            df = fetch_scheme(amfi_code, scheme_name)
            if df is None:
                errors.append(f"{amfi_code}: fetch failed")
                continue

            csv_path = save_raw_csv(df, amfi_code, scheme_name)
            log.info(f"  CSV: {csv_path.name}")

            new_rows = upsert_to_db(df, engine)
            log.info(f"  DB : {new_rows} new rows inserted")

            schemes_fetched += 1
            total_new_rows  += new_rows

            latest = df.iloc[-1]
            summary_rows.append({
                "amfi_code"  : amfi_code,
                "scheme_name": scheme_name,
                "latest_nav" : round(latest["nav"], 4),
                "nav_date"   : latest["date"].date(),
                "new_rows"   : new_rows,
            })

        except Exception as exc:
            log.error(f"  [{amfi_code}] Error: {exc}")
            errors.append(f"{amfi_code}: {exc}")

        time.sleep(DELAY_SEC)

    # Save summary CSV
    run_end = datetime.now()
    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(
            RAW_DIR / "live_nav_summary.csv", index=False
        )

    # Log to DB
    status = ("SUCCESS" if not errors
              else "PARTIAL" if schemes_fetched > 0
              else "FAILED")
    log_run_to_db(engine, run_start.strftime("%Y-%m-%d %H:%M:%S"),
                  schemes_fetched, total_new_rows, status,
                  "; ".join(errors))

    duration = (run_end - run_start).seconds
    log.info("=" * 65)
    log.info(f"  STATUS   : {status}")
    log.info(f"  Schemes  : {schemes_fetched}/{len(SCHEMES)}")
    log.info(f"  New rows : {total_new_rows}")
    log.info(f"  Duration : {duration}s")
    if errors:
        log.info(f"  Errors   : {errors}")
    log.info("=" * 65)


# ═════════════════════════════════════════════════════════════
# SECTION 3 — SCHEDULER
# ═════════════════════════════════════════════════════════════

def start_scheduler():
    """Start the continuous scheduler — runs until Ctrl+C."""
    log.info("=" * 65)
    log.info("  BLUESTOCK ETL SCHEDULER")
    log.info(f"  Schedule : Every weekday Mon-Fri at {RUN_TIME}")
    log.info(f"  Schemes  : {len(SCHEMES)}")
    log.info(f"  Database : {DB_PATH}")
    log.info(f"  Log      : {LOG_FILE}")
    log.info("  Press Ctrl+C to stop")
    log.info("=" * 65)

    schedule.every().monday.at(RUN_TIME).do(run_etl_job)
    schedule.every().tuesday.at(RUN_TIME).do(run_etl_job)
    schedule.every().wednesday.at(RUN_TIME).do(run_etl_job)
    schedule.every().thursday.at(RUN_TIME).do(run_etl_job)
    schedule.every().friday.at(RUN_TIME).do(run_etl_job)

    log.info(f"  Next run : {schedule.next_run()}")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("Scheduler stopped by user.")


# ═════════════════════════════════════════════════════════════
# SECTION 4 — WINDOWS TASK SCHEDULER SETUP
# ═════════════════════════════════════════════════════════════

def setup_windows_task():
    """Register this script as a Windows Task Scheduler job."""
    if sys.platform != "win32":
        print("Windows Task Scheduler is only available on Windows.")
        print("On Linux/Mac, use crontab instead:")
        print(f"  0 20 * * 1-5 cd $(pwd) && python3 etl_scheduler.py --run-now")
        return

    python_path  = sys.executable
    script_path  = str(Path(__file__).resolve())
    project_dir  = str(Path(__file__).parent.resolve())

    # Build schtasks command
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{python_path}" "{script_path}" --run-now',
        "/sc", "WEEKLY",
        "/d", "MON,TUE,WED,THU,FRI",
        "/st", RUN_TIME,
        "/rl", "HIGHEST",
        "/f",
    ]

    print(f"\nRegistering Windows Task: {TASK_NAME}")
    print(f"Script  : {script_path}")
    print(f"Python  : {python_path}")
    print(f"Schedule: Every weekday at {RUN_TIME}")
    print()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("Task registered successfully!")
            print()
            print("The ETL will now run automatically every weekday at 8 PM.")
            print("Even when VS Code is closed.")
            print()
            print("To verify:")
            print("  Open Task Scheduler from Windows Start Menu")
            print(f"  Look for: {TASK_NAME}")
            print()
            print("To test immediately:")
            print("  python etl_scheduler.py --run-now")
        else:
            print(f"ERROR: {result.stderr}")
            print()
            print("Try running as Administrator:")
            print("  Right-click your terminal -> Run as Administrator")
            print("  Then run: python etl_scheduler.py --setup-windows")
    except FileNotFoundError:
        print("schtasks not found. Make sure you are on Windows.")


def remove_windows_task():
    """Remove the Windows Task Scheduler job."""
    if sys.platform != "win32":
        print("Not on Windows. Remove your crontab entry manually.")
        return
    cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' removed successfully.")
    else:
        print(f"Could not remove task: {result.stderr}")


# ═════════════════════════════════════════════════════════════
# SECTION 5 — STATUS & HISTORY COMMANDS
# ═════════════════════════════════════════════════════════════

def show_status():
    """Show the last ETL run status from DB."""
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        with engine.connect() as conn:
            df = pd.read_sql(
                "SELECT * FROM etl_run_log ORDER BY id DESC LIMIT 1",
                conn
            )
        if df.empty:
            print("No ETL runs recorded yet.")
            print("Run: python etl_scheduler.py --run-now")
        else:
            row = df.iloc[0]
            print()
            print("=" * 50)
            print("  LAST ETL RUN STATUS")
            print("=" * 50)
            print(f"  Timestamp       : {row['run_timestamp']}")
            print(f"  Status          : {row['status']}")
            print(f"  Schemes fetched : {row['schemes_fetched']}")
            print(f"  New NAV rows    : {row['new_nav_rows']}")
            if row['error_msg']:
                print(f"  Errors          : {row['error_msg']}")
            print("=" * 50)
    except Exception as exc:
        print(f"Could not read status: {exc}")
        print(f"DB path: {DB_PATH}")


def show_history():
    """Show last 10 ETL run records from DB."""
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        with engine.connect() as conn:
            df = pd.read_sql(
                "SELECT * FROM etl_run_log ORDER BY id DESC LIMIT 10",
                conn
            )
        if df.empty:
            print("No ETL run history found.")
        else:
            print()
            print("LAST 10 ETL RUNS:")
            print(df.to_string(index=False))
    except Exception as exc:
        print(f"Could not read history: {exc}")


# ═════════════════════════════════════════════════════════════
# SECTION 6 — ENTRY POINT
# ═════════════════════════════════════════════════════════════

def print_help():
    print("""
Bluestock ETL Scheduler — Usage
================================
python etl_scheduler.py               Start scheduler (8 PM weekdays)
python etl_scheduler.py --run-now     Run ETL immediately (test)
python etl_scheduler.py --setup-windows  Register Windows Task
python etl_scheduler.py --remove-windows Remove Windows Task
python etl_scheduler.py --status      Show last run status
python etl_scheduler.py --history     Show last 10 runs
python etl_scheduler.py --help        Show this help
""")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "--run-now":
        log.info("Manual trigger: --run-now")
        run_etl_job()

    elif arg == "--setup-windows":
        setup_windows_task()

    elif arg == "--remove-windows":
        remove_windows_task()

    elif arg == "--status":
        show_status()

    elif arg == "--history":
        show_history()

    elif arg == "--help":
        print_help()

    elif arg == "":
        start_scheduler()

    else:
        print(f"Unknown argument: {arg}")
        print_help()