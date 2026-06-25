# Data Dictionary — Mutual Fund Analytics
**Project:** Bluestock Mutual Fund Analytics  
**Database:** `bluestock_mf.db`  
**Last Updated:** Day 2  
**Author:** Mayank

---

## Table of Contents
1. [01 — fund_master](#1-fund_master)
2. [02 — nav_history](#2-nav_history)
3. [03 — aum_by_fund_house](#3-aum_by_fund_house)
4. [04 — monthly_sip_inflows](#4-monthly_sip_inflows)
5. [05 — category_inflows](#5-category_inflows)
6. [06 — industry_folio_count](#6-industry_folio_count)
7. [07 — scheme_performance](#7-scheme_performance)
8. [08 — investor_transactions](#8-investor_transactions)
9. [09 — portfolio_holdings](#9-portfolio_holdings)
10. [10 — benchmark_indices](#10-benchmark_indices)

---

## 1. fund_master

**Source file:** `data/raw/01_fund_master.csv`  
**Processed:** `data/processed/01_fund_master.csv`  
**DB Table:** `dim_fund`  
**Shape:** 40 rows × 15 columns  
**Description:** Master reference table for all 40 mutual fund schemes across 10 AMCs. One row per scheme.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `amfi_code` | INTEGER (PK) | Unique 6-digit scheme code assigned by AMFI (Association of Mutual Funds in India) | `125497` |
| `fund_house` | TEXT | Name of the Asset Management Company (AMC) managing the scheme | `HDFC Mutual Fund` |
| `scheme_name` | TEXT | Full official name of the mutual fund scheme as registered with SEBI | `HDFC Top 100 Fund Direct Growth` |
| `category` | TEXT | Broad SEBI asset class category. Values: `Equity`, `Debt` | `Equity` |
| `sub_category` | TEXT | SEBI sub-classification within the category. Values: Large Cap, Mid Cap, Small Cap, Large & Mid Cap, Flexi Cap, ELSS, Value, Index, Index/ETF, Gilt, Short Duration, Liquid | `Large Cap` |
| `plan` | TEXT | Distribution plan type. Values: `Regular`, `Direct`. Direct plans have lower expense ratios as no distributor commission is paid | `Direct` |
| `launch_date` | DATE | Date the scheme was launched and made available for investment | `2013-01-01` |
| `benchmark` | TEXT | Index used to measure scheme performance. e.g. NIFTY100, NIFTY50 | `NIFTY100` |
| `expense_ratio_pct` | REAL | Annual fee charged to manage the fund as a % of AUM. Valid range: 0.1%–2.5% per SEBI regulations | `0.55` |
| `exit_load_pct` | REAL | Fee charged on redemption within a specified period (typically 1 year). 0 = no exit load | `1.0` |
| `min_sip_amount` | REAL | Minimum amount (INR) required per SIP instalment | `500` |
| `min_lumpsum_amount` | REAL | Minimum one-time investment amount in INR | `5000` |
| `fund_manager` | TEXT | Name of the fund manager responsible for investment decisions | `Prashant Jain` |
| `risk_category` | TEXT | SEBI-mandated risk label. Values: Low, Moderate, Moderately High, High, Very High | `Very High` |
| `sebi_category_code` | TEXT | SEBI internal category classification code | `EQ-LC-01` |

---

## 2. nav_history

**Source file:** `data/raw/02_nav_history.csv`  
**Processed:** `data/processed/02_nav_history.csv`  
**DB Table:** `fact_nav`  
**Shape:** 46,000 rows × 3 columns (raw); ~150,000+ after forward-fill  
**Description:** Daily Net Asset Value (NAV) for each scheme. Forward-filled for weekends and public holidays.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `amfi_code` | INTEGER (FK → dim_fund) | AMFI scheme code linking to dim_fund | `125497` |
| `date` | DATE | Trading date in YYYY-MM-DD format. Parsed from string during cleaning | `2024-03-15` |
| `nav` | REAL | NAV per unit in INR. Must be > 0. Represents the per-unit market value of the fund on that date | `842.3571` |

**Cleaning notes:**
- Dates parsed to `datetime` using `%Y-%m-%d` format
- Sorted by `amfi_code` + `date`
- Forward-filled for weekends/holidays using `ffill()` per fund group
- Rows with `nav <= 0` removed (none found in source data)

---

## 3. aum_by_fund_house

**Source file:** `data/raw/03_aum_by_fund_house.csv`  
**Processed:** `data/processed/03_aum_by_fund_house.csv`  
**DB Table:** `fact_aum`  
**Shape:** 90 rows × 5 columns  
**Description:** Quarterly AUM (Assets Under Management) snapshot per fund house.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `date` | DATE | Quarter-end date of the AUM snapshot | `2024-03-31` |
| `fund_house` | TEXT | Name of the AMC | `HDFC Mutual Fund` |
| `aum_lakh_crore` | REAL | AUM expressed in lakh crore INR (1 lakh crore = 10 trillion INR) | `5.23` |
| `aum_crore` | REAL | AUM expressed in crore INR (1 crore = 10 million INR) | `523000` |
| `num_schemes` | INTEGER | Number of active schemes offered by the fund house on that date | `4` |

---

## 4. monthly_sip_inflows

**Source file:** `data/raw/04_monthly_sip_inflows.csv`  
**Processed:** `data/processed/04_monthly_sip_inflows.csv`  
**DB Table:** `fact_sip_inflows`  
**Shape:** 48 rows × 6 columns  
**Description:** Industry-wide monthly SIP (Systematic Investment Plan) inflow statistics.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `month` | TEXT (YYYY-MM) | Reference month for SIP data | `2024-03` |
| `sip_inflow_crore` | REAL | Total SIP contributions received industry-wide in that month (INR crore) | `19270.5` |
| `active_sip_accounts_crore` | REAL | Total active SIP accounts across all AMCs (in crore units) | `0.87` |
| `new_sip_accounts_lakh` | REAL | New SIP accounts registered in that month (in lakh units) | `28.5` |
| `sip_aum_lakh_crore` | REAL | Total AUM attributable to SIP investments (lakh crore INR) | `10.2` |
| `yoy_growth_pct` | REAL | Year-over-year percentage growth in SIP inflows. **NULL for first 12 rows (Jan–Dec 2022)** — expected, no prior-year baseline available | `18.5` |

**Known anomaly:** `yoy_growth_pct` is NULL for rows 1–12. This is intentional and expected.

---

## 5. category_inflows

**Source file:** `data/raw/05_category_inflows.csv`  
**Processed:** `data/processed/05_category_inflows.csv`  
**DB Table:** `fact_category_inflows`  
**Shape:** 144 rows × 3 columns  
**Description:** Monthly net inflows by fund category across the industry.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `month` | TEXT (YYYY-MM) | Reference month | `2024-03` |
| `category` | TEXT | Fund category. Values: Large Cap, Mid Cap, Small Cap, Flexi Cap, Large & Mid Cap, ELSS, Value/Contra, Sectoral/Thematic, Liquid, Short Duration, Gilt, Hybrid | `Large Cap` |
| `net_inflow_crore` | REAL | Net inflows into this category in that month (INR crore). Negative = net outflow (redemptions > purchases) | `3500.25` |

---

## 6. industry_folio_count

**Source file:** `data/raw/06_industry_folio_count.csv`  
**Processed:** `data/processed/06_industry_folio_count.csv`  
**DB Table:** `fact_industry_folio`  
**Shape:** 21 rows × 6 columns  
**Description:** Quarterly count of investor folios (accounts) across asset classes.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `month` | TEXT (YYYY-MM) | Quarter reference period | `2024-01` |
| `total_folios_crore` | REAL | Total investor folios industry-wide (in crore units) | `17.8` |
| `equity_folios_crore` | REAL | Folios invested in equity schemes (crore) | `12.3` |
| `debt_folios_crore` | REAL | Folios invested in debt schemes (crore) | `2.1` |
| `hybrid_folios_crore` | REAL | Folios invested in hybrid schemes (crore) | `2.8` |
| `others_folios_crore` | REAL | Folios in other scheme types — ETFs, FoFs, etc. (crore) | `0.6` |

---

## 7. scheme_performance

**Source file:** `data/raw/07_scheme_performance.csv`  
**Processed:** `data/processed/07_scheme_performance.csv`  
**DB Table:** `fact_performance`  
**Shape:** 40 rows × 19 columns (+ 4 derived flag columns after cleaning)  
**Description:** Risk and return metrics for all 40 schemes as of the latest available date.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `amfi_code` | INTEGER (FK) | AMFI scheme code | `125497` |
| `scheme_name` | TEXT | Scheme name | `HDFC Top 100 Fund Direct` |
| `fund_house` | TEXT | AMC name | `HDFC Mutual Fund` |
| `category` | TEXT | Asset category | `Equity` |
| `plan` | TEXT | Regular or Direct | `Direct` |
| `return_1yr_pct` | REAL | Absolute returns over the past 1 year (%) | `18.45` |
| `return_3yr_pct` | REAL | CAGR over the past 3 years (%) | `14.22` |
| `return_5yr_pct` | REAL | CAGR over the past 5 years (%) | `16.80` |
| `benchmark_3yr_pct` | REAL | 3-year CAGR of the scheme's benchmark index (%) | `12.50` |
| `alpha` | REAL | Excess return over benchmark. Positive = outperformance | `1.72` |
| `beta` | REAL | Sensitivity to market movements. Beta=1 moves in line with market | `0.92` |
| `sharpe_ratio` | REAL | Risk-adjusted return = (return - risk-free rate) / std deviation. Higher is better | `1.45` |
| `sortino_ratio` | REAL | Like Sharpe but only penalises downside volatility. Higher is better | `1.82` |
| `std_dev_ann_pct` | REAL | Annualised standard deviation of returns — measure of volatility (%) | `14.3` |
| `max_drawdown_pct` | REAL | Largest peak-to-trough decline in NAV (%). Negative value; e.g. -22.5 means 22.5% drop | `-22.5` |
| `aum_crore` | REAL | Current Assets Under Management (INR crore) | `28450` |
| `expense_ratio_pct` | REAL | Annual management fee as % of AUM. Valid range per SEBI: 0.1%–2.5% | `0.75` |
| `morningstar_rating` | INTEGER | Morningstar star rating 1–5. 5 = top 10% of category | `4` |
| `risk_grade` | TEXT | SEBI risk grade. Values: Low, Moderate, Moderately High, High, Very High | `High` |
| `beats_benchmark` | INTEGER | **Derived.** 1 if alpha > 0 (outperforms benchmark), else 0 | `1` |
| `alpha_flag` | INTEGER | **Derived.** 1 if alpha < -3 (severe underperformance flag) | `0` |
| `drawdown_flag` | INTEGER | **Derived.** 1 if max_drawdown_pct < -30% (high risk flag) | `0` |
| `neg_5yr_flag` | INTEGER | **Derived.** 1 if return_5yr_pct < 0 (negative long-term return) | `0` |

---

## 8. investor_transactions

**Source file:** `data/raw/08_investor_transactions.csv`  
**Processed:** `data/processed/08_investor_transactions.csv`  
**DB Table:** `fact_transactions`  
**Shape:** 32,778 rows × 13 columns  
**Description:** Individual investor transaction records (purchases and redemptions).

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `investor_id` | TEXT | Anonymised unique investor identifier | `INV_00142` |
| `transaction_date` | DATE | Date the transaction was executed. Parsed to datetime | `2024-03-15` |
| `amfi_code` | INTEGER (FK) | Scheme the transaction was made in | `125497` |
| `transaction_type` | TEXT | Type of transaction. Standardised values: `SIP`, `Lumpsum`, `Redemption` | `SIP` |
| `amount_inr` | REAL | Transaction amount in INR. Must be > 0 | `5000.00` |
| `state` | TEXT | Indian state where the investor is registered | `Maharashtra` |
| `city` | TEXT | City of the investor | `Mumbai` |
| `city_tier` | TEXT | AMFI city classification. `T30` = Top 30 cities, `B30` = Beyond Top 30 cities | `T30` |
| `age_group` | TEXT | Investor age bracket. Values: 18-25, 26-35, 36-45, 46-55, 56+ | `26-35` |
| `gender` | TEXT | Investor gender | `Male` |
| `annual_income_lakh` | REAL | Investor's annual income in lakh INR | `12.5` |
| `payment_mode` | TEXT | Payment method. Values: UPI, Cheque, Mandate, Net Banking | `UPI` |
| `kyc_status` | TEXT | KYC verification status. Values: `Verified`, `Pending`, `Rejected` | `Verified` |

---

## 9. portfolio_holdings

**Source file:** `data/raw/09_portfolio_holdings.csv`  
**Processed:** `data/processed/09_portfolio_holdings.csv`  
**DB Table:** `fact_portfolio_holdings`  
**Shape:** 322 rows × 8 columns  
**Description:** Stock-level portfolio holdings for equity funds showing what each fund owns.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `amfi_code` | INTEGER (FK) | AMFI scheme code of the fund holding this stock | `125497` |
| `stock_symbol` | TEXT | NSE/BSE ticker symbol of the stock | `RELIANCE` |
| `stock_name` | TEXT | Full name of the company | `Reliance Industries Ltd` |
| `sector` | TEXT | Business sector. Values: Banking, IT, FMCG, Pharma, Automobile, Energy, Telecom, Infrastructure, NBFC, Cement, Consumer Goods, Utilities, Diversified, Paints | `Banking` |
| `weight_pct` | REAL | Percentage of the fund's portfolio allocated to this stock (%) | `8.45` |
| `market_value_cr` | REAL | Market value of the holding in INR crore | `2412.5` |
| `current_price_inr` | REAL | Current market price per share in INR | `2850.75` |
| `portfolio_date` | DATE | Date as of which the portfolio disclosure is valid | `2024-03-31` |

---

## 10. benchmark_indices

**Source file:** `data/raw/10_benchmark_indices.csv`  
**Processed:** `data/processed/10_benchmark_indices.csv`  
**DB Table:** `fact_benchmark_indices`  
**Shape:** 8,050 rows × 3 columns  
**Description:** Daily closing values for 7 benchmark indices used to measure fund performance.

| Column | Type | Business Definition | Example |
|--------|------|---------------------|---------|
| `date` | DATE | Trading date. Parsed from string to datetime | `2024-03-15` |
| `index_name` | TEXT | Name of the index. Values: NIFTY50, NIFTY100, NIFTY_MIDCAP150, BSE_SMALLCAP, NIFTY500, CRISIL_LIQUID, CRISIL_GILT | `NIFTY50` |
| `close_value` | REAL | Index closing value on that trading day | `22412.40` |

---

## Relationships (Star Schema)

```
dim_fund (amfi_code PK)
    ├── fact_nav          (amfi_code FK, date_id FK)
    ├── fact_transactions (amfi_code FK, date_id FK)
    ├── fact_performance  (amfi_code FK)
    └── fact_portfolio_holdings (amfi_code FK)

dim_date (date_id PK)
    ├── fact_nav
    ├── fact_transactions
    ├── fact_aum
    └── fact_benchmark_indices
```

---

## Data Quality Summary

| Dataset | Rows | Nulls | Duplicates | Issues |
|---------|------|-------|------------|--------|
| fund_master | 40 | 0 | 0 | None |
| nav_history | 46,000 (raw) | 0 | 0 | Date strings → parsed; gaps forward-filled |
| aum_by_fund_house | 90 | 0 | 0 | None |
| monthly_sip_inflows | 48 | 12 | 0 | yoy_growth_pct NULL for first 12 months (expected) |
| category_inflows | 144 | 0 | 0 | None |
| industry_folio_count | 21 | 0 | 0 | None |
| scheme_performance | 40 | 0 | 0 | 4 derived flag columns added |
| investor_transactions | 32,778 | 0 | 0 | Date strings → parsed |
| portfolio_holdings | 322 | 0 | 0 | None |
| benchmark_indices | 8,050 | 0 | 0 | Date strings → parsed |