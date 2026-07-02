#!/usr/bin/env python3
"""
recommender.py -- Simple Fund Recommender
==========================================
Input:  risk appetite (Low / Moderate / High)
Output: top N funds by Sharpe ratio within the matching risk_grade

Standalone, zero-dependency (stdlib only). FUND_DATA below is a snapshot of
the fund-level Sharpe ratios computed in Advanced_Analytics.ipynb (Task 5),
from a seeded SYNTHETIC dataset -- see the notebook for the full pipeline,
methodology notes, and the disclaimer on real vs. demo data.

Sharpe here = mean(daily_return) / std(daily_return) * sqrt(252), annualized,
with NO risk-free rate subtracted (matches the rolling-Sharpe formula used
in the notebook) -- so read it as a return-consistency score, not a
textbook excess-return Sharpe.

Usage:
    python recommender.py                    # prints all 3 risk tiers, top 3 each
    python recommender.py --risk Moderate     # just one tier
    python recommender.py --risk High --top 5 # top 5 instead of top 3

In production, replace FUND_DATA with a live query against your fund
database / metrics warehouse instead of this hardcoded snapshot.
"""
import argparse

# Snapshot from Advanced_Analytics.ipynb Task 5 (synthetic demo data)
FUND_DATA = [
    {"fund_id": "F001", "fund_name": "Meridian Large Cap Fund", "category": "Large Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.342},
    {"fund_id": "F002", "fund_name": "Zenith Large Cap Fund", "category": "Large Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.22},
    {"fund_id": "F003", "fund_name": "Horizon Large Cap Fund", "category": "Large Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.482},
    {"fund_id": "F004", "fund_name": "Summit Large Cap Fund", "category": "Large Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.212},
    {"fund_id": "F005", "fund_name": "Northstar Flexi Cap Fund", "category": "Flexi Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.213},
    {"fund_id": "F006", "fund_name": "Everest Flexi Cap Fund", "category": "Flexi Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.182},
    {"fund_id": "F007", "fund_name": "Compass Flexi Cap Fund", "category": "Flexi Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.309},
    {"fund_id": "F008", "fund_name": "Pinnacle Flexi Cap Fund", "category": "Flexi Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.3},
    {"fund_id": "F009", "fund_name": "Vertex Multi Cap Fund", "category": "Multi Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.455},
    {"fund_id": "F010", "fund_name": "Beacon Multi Cap Fund", "category": "Multi Cap", "risk_grade": "Moderate", "sharpe_ratio": 0.478},
    {"fund_id": "F011", "fund_name": "Meridian Mid Cap Fund", "category": "Mid Cap", "risk_grade": "High", "sharpe_ratio": 0.466},
    {"fund_id": "F012", "fund_name": "Zenith Mid Cap Fund", "category": "Mid Cap", "risk_grade": "High", "sharpe_ratio": 1.019},
    {"fund_id": "F013", "fund_name": "Horizon Mid Cap Fund", "category": "Mid Cap", "risk_grade": "High", "sharpe_ratio": 0.228},
    {"fund_id": "F014", "fund_name": "Summit Small Cap Fund", "category": "Small Cap", "risk_grade": "High", "sharpe_ratio": 0.191},
    {"fund_id": "F015", "fund_name": "Northstar Small Cap Fund", "category": "Small Cap", "risk_grade": "High", "sharpe_ratio": 0.909},
    {"fund_id": "F016", "fund_name": "Everest Small Cap Fund", "category": "Small Cap", "risk_grade": "High", "sharpe_ratio": 0.611},
    {"fund_id": "F017", "fund_name": "Compass Sectoral - Banking Fund", "category": "Sectoral - Banking", "risk_grade": "High", "sharpe_ratio": 0.766},
    {"fund_id": "F018", "fund_name": "Pinnacle Sectoral - IT Fund", "category": "Sectoral - IT", "risk_grade": "High", "sharpe_ratio": 0.111},
    {"fund_id": "F019", "fund_name": "Vertex Sectoral - Pharma Fund", "category": "Sectoral - Pharma", "risk_grade": "High", "sharpe_ratio": 0.26},
    {"fund_id": "F020", "fund_name": "Beacon ELSS Fund", "category": "ELSS", "risk_grade": "High", "sharpe_ratio": 0.46},
    {"fund_id": "F021", "fund_name": "Meridian Liquid Fund", "category": "Liquid", "risk_grade": "Low", "sharpe_ratio": 2.008},
    {"fund_id": "F022", "fund_name": "Zenith Liquid Fund", "category": "Liquid", "risk_grade": "Low", "sharpe_ratio": 2.014},
    {"fund_id": "F023", "fund_name": "Horizon Ultra Short Duration Fund", "category": "Ultra Short Duration", "risk_grade": "Low", "sharpe_ratio": 1.993},
    {"fund_id": "F024", "fund_name": "Summit Ultra Short Duration Fund", "category": "Ultra Short Duration", "risk_grade": "Low", "sharpe_ratio": 2.075},
    {"fund_id": "F025", "fund_name": "Northstar Short Duration Fund", "category": "Short Duration", "risk_grade": "Low", "sharpe_ratio": 1.79},
    {"fund_id": "F026", "fund_name": "Everest Short Duration Fund", "category": "Short Duration", "risk_grade": "Low", "sharpe_ratio": 1.559},
    {"fund_id": "F027", "fund_name": "Compass Corporate Bond Fund", "category": "Corporate Bond", "risk_grade": "Low", "sharpe_ratio": 2.025},
    {"fund_id": "F028", "fund_name": "Pinnacle Corporate Bond Fund", "category": "Corporate Bond", "risk_grade": "Low", "sharpe_ratio": 1.638},
    {"fund_id": "F029", "fund_name": "Vertex Banking & PSU Fund", "category": "Banking & PSU", "risk_grade": "Low", "sharpe_ratio": 2.003},
    {"fund_id": "F030", "fund_name": "Beacon Banking & PSU Fund", "category": "Banking & PSU", "risk_grade": "Low", "sharpe_ratio": 2.031},
    {"fund_id": "F031", "fund_name": "Meridian Gilt Fund", "category": "Gilt", "risk_grade": "Moderate", "sharpe_ratio": 1.873},
    {"fund_id": "F032", "fund_name": "Zenith Dynamic Bond Fund", "category": "Dynamic Bond", "risk_grade": "Moderate", "sharpe_ratio": 1.278},
    {"fund_id": "F033", "fund_name": "Horizon Aggressive Hybrid Fund", "category": "Aggressive Hybrid", "risk_grade": "Moderate", "sharpe_ratio": 0.2},
    {"fund_id": "F034", "fund_name": "Summit Aggressive Hybrid Fund", "category": "Aggressive Hybrid", "risk_grade": "Moderate", "sharpe_ratio": 0.491},
    {"fund_id": "F035", "fund_name": "Northstar Aggressive Hybrid Fund", "category": "Aggressive Hybrid", "risk_grade": "Moderate", "sharpe_ratio": 0.475},
    {"fund_id": "F036", "fund_name": "Everest Conservative Hybrid Fund", "category": "Conservative Hybrid", "risk_grade": "Low", "sharpe_ratio": 0.781},
    {"fund_id": "F037", "fund_name": "Compass Conservative Hybrid Fund", "category": "Conservative Hybrid", "risk_grade": "Low", "sharpe_ratio": 1.038},
    {"fund_id": "F038", "fund_name": "Pinnacle Balanced Advantage Fund", "category": "Balanced Advantage", "risk_grade": "Moderate", "sharpe_ratio": 0.486},
    {"fund_id": "F039", "fund_name": "Vertex Balanced Advantage Fund", "category": "Balanced Advantage", "risk_grade": "Moderate", "sharpe_ratio": 0.523},
    {"fund_id": "F040", "fund_name": "Beacon Equity Savings Fund", "category": "Equity Savings", "risk_grade": "Low", "sharpe_ratio": 0.712},
]

VALID_RISK_GRADES = ("Low", "Moderate", "High")


def recommend_funds(risk_appetite, n=3, fund_data=FUND_DATA):
    """Return the top-n funds by Sharpe ratio within a given risk_grade.

    Parameters
    ----------
    risk_appetite : str
        One of "Low", "Moderate", "High".
    n : int
        Number of funds to return (default 3).
    fund_data : list[dict]
        Fund records with at least fund_id, fund_name, category,
        risk_grade, sharpe_ratio. Defaults to the embedded snapshot.
    """
    if risk_appetite not in VALID_RISK_GRADES:
        raise ValueError(f"risk_appetite must be one of {VALID_RISK_GRADES}, got {risk_appetite!r}")
    matches = [f for f in fund_data if f["risk_grade"] == risk_appetite]
    matches.sort(key=lambda f: f["sharpe_ratio"], reverse=True)
    return matches[:n]


def print_recommendation_table(risk_appetite, n=3):
    """Print a formatted recommendation table for one risk appetite."""
    recs = recommend_funds(risk_appetite, n)
    print(f"\nTop {len(recs)} recommended funds -- {risk_appetite} risk appetite")
    print("-" * 74)
    print(f"{'Fund ID':<8} {'Fund Name':<34} {'Category':<20} {'Sharpe':>7}")
    print("-" * 74)
    for f in recs:
        print(f"{f['fund_id']:<8} {f['fund_name']:<34} {f['category']:<20} {f['sharpe_ratio']:>7.3f}")
    print("-" * 74)


def main():
    parser = argparse.ArgumentParser(description="Simple fund recommender by risk appetite.")
    parser.add_argument("--risk", choices=VALID_RISK_GRADES, default=None,
                         help="Risk appetite: Low, Moderate, or High. Omit to print all three.")
    parser.add_argument("--top", type=int, default=3, help="Number of funds to recommend (default 3).")
    args = parser.parse_args()

    risk_tiers = [args.risk] if args.risk else list(VALID_RISK_GRADES)
    for tier in risk_tiers:
        print_recommendation_table(tier, args.top)


if __name__ == "__main__":
    main()
