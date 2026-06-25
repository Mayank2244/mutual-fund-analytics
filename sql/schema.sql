-- =============================================================
-- schema.sql
-- Day 2 Step 4 — SQLite Star Schema for Mutual Fund Analytics
-- =============================================================
-- Tables:
--   Dimensions : dim_fund, dim_date
--   Facts      : fact_nav, fact_transactions, fact_performance, fact_aum
-- =============================================================

PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------
-- DIM_FUND  (one row per scheme)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code           INTEGER     PRIMARY KEY,
    fund_house          TEXT        NOT NULL,
    scheme_name         TEXT        NOT NULL,
    category            TEXT        NOT NULL,       -- Equity / Debt
    sub_category        TEXT        NOT NULL,       -- Large Cap / Mid Cap etc.
    plan                TEXT        NOT NULL,       -- Regular / Direct
    launch_date         DATE,
    benchmark           TEXT,
    expense_ratio_pct   REAL,
    exit_load_pct       REAL,
    min_sip_amount      REAL,
    min_lumpsum_amount  REAL,
    fund_manager        TEXT,
    risk_category       TEXT,                       -- Low / Moderate / High etc.
    sebi_category_code  TEXT
);

-- -------------------------------------------------------------
-- DIM_DATE  (one row per calendar day)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id     TEXT    PRIMARY KEY,    -- YYYY-MM-DD
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    day         INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,       -- 1-4
    month_name  TEXT    NOT NULL,       -- January … December
    day_name    TEXT    NOT NULL,       -- Monday … Sunday
    is_weekend  INTEGER NOT NULL        -- 0 = weekday, 1 = weekend
);

-- -------------------------------------------------------------
-- FACT_NAV  (daily NAV per scheme)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code   INTEGER NOT NULL,
    date_id     TEXT    NOT NULL,
    nav         REAL    NOT NULL CHECK (nav > 0),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund (amfi_code),
    FOREIGN KEY (date_id)   REFERENCES dim_date (date_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_nav_amfi ON fact_nav (amfi_code);
CREATE INDEX IF NOT EXISTS idx_fact_nav_date ON fact_nav (date_id);

-- -------------------------------------------------------------
-- FACT_TRANSACTIONS  (investor buy/sell/SIP records)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id         TEXT    NOT NULL,
    amfi_code           INTEGER NOT NULL,
    date_id             TEXT    NOT NULL,
    transaction_type    TEXT    NOT NULL CHECK (transaction_type IN ('SIP','Lumpsum','Redemption')),
    amount_inr          REAL    NOT NULL CHECK (amount_inr > 0),
    state               TEXT,
    city                TEXT,
    city_tier           TEXT    CHECK (city_tier IN ('T30','B30')),
    age_group           TEXT,
    gender              TEXT,
    annual_income_lakh  REAL,
    payment_mode        TEXT,
    kyc_status          TEXT    CHECK (kyc_status IN ('Verified','Pending','Rejected')),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund (amfi_code),
    FOREIGN KEY (date_id)   REFERENCES dim_date (date_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_txn_amfi ON fact_transactions (amfi_code);
CREATE INDEX IF NOT EXISTS idx_fact_txn_date ON fact_transactions (date_id);
CREATE INDEX IF NOT EXISTS idx_fact_txn_type ON fact_transactions (transaction_type);

-- -------------------------------------------------------------
-- FACT_PERFORMANCE  (scheme performance metrics, one row per scheme)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_performance (
    perf_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL,
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    benchmark_3yr_pct   REAL,
    alpha               REAL,
    beta                REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    std_dev_ann_pct     REAL,
    max_drawdown_pct    REAL,
    aum_crore           REAL,
    expense_ratio_pct   REAL,
    morningstar_rating  INTEGER,
    risk_grade          TEXT,
    beats_benchmark     INTEGER,    -- 1 = yes, 0 = no
    alpha_flag          INTEGER,    -- 1 = alpha < -3
    drawdown_flag       INTEGER,    -- 1 = drawdown > 30%
    neg_5yr_flag        INTEGER,    -- 1 = negative 5yr return
    FOREIGN KEY (amfi_code) REFERENCES dim_fund (amfi_code)
);

-- -------------------------------------------------------------
-- FACT_AUM  (monthly AUM by fund house)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id             TEXT    NOT NULL,
    fund_house          TEXT    NOT NULL,
    aum_lakh_crore      REAL,
    aum_crore           REAL,
    num_schemes         INTEGER,
    FOREIGN KEY (date_id) REFERENCES dim_date (date_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_aum_date      ON fact_aum (date_id);
CREATE INDEX IF NOT EXISTS idx_fact_aum_fundhouse ON fact_aum (fund_house);

-- -------------------------------------------------------------
-- FACT_SIP_INFLOWS  (monthly SIP industry data)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sip_inflows (
    sip_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    month                   TEXT    NOT NULL,   -- YYYY-MM
    sip_inflow_crore        REAL,
    active_sip_accounts_crore REAL,
    new_sip_accounts_lakh   REAL,
    sip_aum_lakh_crore      REAL,
    yoy_growth_pct          REAL    -- NULL for first 12 months (expected)
);

-- -------------------------------------------------------------
-- FACT_CATEGORY_INFLOWS  (monthly net inflows by category)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_category_inflows (
    cat_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    month           TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    net_inflow_crore REAL
);

-- -------------------------------------------------------------
-- FACT_PORTFOLIO_HOLDINGS  (stock-level holdings per fund)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_portfolio_holdings (
    holding_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL,
    stock_symbol        TEXT,
    stock_name          TEXT,
    sector              TEXT,
    weight_pct          REAL,
    market_value_cr     REAL,
    current_price_inr   REAL,
    portfolio_date      DATE,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund (amfi_code)
);

-- -------------------------------------------------------------
-- FACT_BENCHMARK_INDICES  (daily index close values)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_benchmark_indices (
    idx_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date_id     TEXT    NOT NULL,
    index_name  TEXT    NOT NULL,
    close_value REAL    NOT NULL,
    FOREIGN KEY (date_id) REFERENCES dim_date (date_id)
);