-- =============================================================
-- queries.sql
-- Day 2 Step 6 — 10 Analytical SQL Queries
-- Database: bluestock_mf.db
-- =============================================================

-- -------------------------------------------------------------
-- Q1. Top 5 funds by AUM (latest available date)
-- -------------------------------------------------------------
SELECT
    f.scheme_name,
    f.fund_house,
    f.category,
    f.sub_category,
    p.aum_crore,
    p.morningstar_rating,
    p.return_3yr_pct
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.aum_crore DESC
LIMIT 5;

-- -------------------------------------------------------------
-- Q2. Average NAV per month per fund (last 12 months)
-- -------------------------------------------------------------
SELECT
    f.scheme_name,
    d.year,
    d.month,
    d.month_name,
    ROUND(AVG(n.nav), 4)  AS avg_nav,
    ROUND(MIN(n.nav), 4)  AS min_nav,
    ROUND(MAX(n.nav), 4)  AS max_nav
FROM fact_nav n
JOIN dim_fund f ON f.amfi_code = n.amfi_code
JOIN dim_date d ON d.date_id   = n.date_id
WHERE d.date_id >= DATE('now', '-12 months')
GROUP BY f.scheme_name, d.year, d.month
ORDER BY f.scheme_name, d.year, d.month;

-- -------------------------------------------------------------
-- Q3. SIP inflow YoY growth (month by month)
-- -------------------------------------------------------------
SELECT
    month,
    ROUND(sip_inflow_crore, 2)          AS sip_inflow_crore,
    ROUND(active_sip_accounts_crore, 4) AS active_accounts_crore,
    ROUND(new_sip_accounts_lakh, 2)     AS new_accounts_lakh,
    ROUND(yoy_growth_pct, 2)            AS yoy_growth_pct
FROM fact_sip_inflows
ORDER BY month;

-- -------------------------------------------------------------
-- Q4. Total transaction amount and count by state
-- -------------------------------------------------------------
SELECT
    t.state,
    t.city_tier,
    COUNT(*)                            AS total_transactions,
    ROUND(SUM(t.amount_inr), 2)         AS total_amount_inr,
    ROUND(AVG(t.amount_inr), 2)         AS avg_amount_inr,
    COUNT(DISTINCT t.investor_id)       AS unique_investors
FROM fact_transactions t
GROUP BY t.state, t.city_tier
ORDER BY total_amount_inr DESC;

-- -------------------------------------------------------------
-- Q5. Funds with expense_ratio < 1% (most cost-efficient)
-- -------------------------------------------------------------
SELECT
    f.scheme_name,
    f.fund_house,
    f.category,
    f.sub_category,
    f.plan,
    f.expense_ratio_pct,
    p.return_3yr_pct,
    p.morningstar_rating
FROM dim_fund f
JOIN fact_performance p ON p.amfi_code = f.amfi_code
WHERE f.expense_ratio_pct < 1.0
ORDER BY f.expense_ratio_pct ASC;

-- -------------------------------------------------------------
-- Q6. Best performing funds — top 10 by 3-year return
-- -------------------------------------------------------------
SELECT
    f.scheme_name,
    f.fund_house,
    f.sub_category,
    f.plan,
    p.return_1yr_pct,
    p.return_3yr_pct,
    p.return_5yr_pct,
    p.benchmark_3yr_pct,
    ROUND(p.return_3yr_pct - p.benchmark_3yr_pct, 2) AS alpha_vs_benchmark,
    p.sharpe_ratio,
    p.morningstar_rating
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.return_3yr_pct DESC
LIMIT 10;

-- -------------------------------------------------------------
-- Q7. AUM trend by fund house (quarterly)
-- -------------------------------------------------------------
SELECT
    a.fund_house,
    d.year,
    d.quarter,
    ROUND(AVG(a.aum_crore), 2)          AS avg_aum_crore,
    ROUND(MAX(a.aum_crore), 2)          AS peak_aum_crore,
    ROUND(MIN(a.aum_crore), 2)          AS trough_aum_crore
FROM fact_aum a
JOIN dim_date d ON d.date_id = a.date_id
GROUP BY a.fund_house, d.year, d.quarter
ORDER BY a.fund_house, d.year, d.quarter;

-- -------------------------------------------------------------
-- Q8. SIP vs Lumpsum vs Redemption breakdown by month
-- -------------------------------------------------------------
SELECT
    d.year,
    d.month,
    d.month_name,
    t.transaction_type,
    COUNT(*)                            AS num_transactions,
    ROUND(SUM(t.amount_inr), 2)         AS total_amount_inr,
    ROUND(AVG(t.amount_inr), 2)         AS avg_amount_inr
FROM fact_transactions t
JOIN dim_date d ON d.date_id = t.date_id
GROUP BY d.year, d.month, t.transaction_type
ORDER BY d.year, d.month, t.transaction_type;

-- -------------------------------------------------------------
-- Q9. Top 5 sectors by portfolio weight (across all funds)
-- -------------------------------------------------------------
SELECT
    h.sector,
    COUNT(DISTINCT h.amfi_code)          AS num_funds,
    COUNT(DISTINCT h.stock_symbol)       AS num_stocks,
    ROUND(AVG(h.weight_pct), 2)          AS avg_weight_pct,
    ROUND(SUM(h.market_value_cr), 2)     AS total_market_value_cr
FROM fact_portfolio_holdings h
GROUP BY h.sector
ORDER BY total_market_value_cr DESC
LIMIT 5;

-- -------------------------------------------------------------
-- Q10. Risk-adjusted performance — Sharpe ratio ranking
--      with category breakdown
-- -------------------------------------------------------------
SELECT
    f.scheme_name,
    f.fund_house,
    f.sub_category,
    f.risk_category,
    p.sharpe_ratio,
    p.sortino_ratio,
    p.beta,
    p.std_dev_ann_pct,
    p.max_drawdown_pct,
    p.return_5yr_pct,
    p.morningstar_rating,
    CASE
        WHEN p.sharpe_ratio >= 1.5 THEN 'Excellent'
        WHEN p.sharpe_ratio >= 1.0 THEN 'Good'
        WHEN p.sharpe_ratio >= 0.5 THEN 'Average'
        ELSE 'Poor'
    END AS sharpe_grade
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.sharpe_ratio DESC;