"""
recommender.py
==============
Day 6 — Simple Fund Recommender
Input  : risk appetite (Low / Moderate / High)
Output : Top 3 funds by Sharpe ratio within matching risk grade

Run:
    python recommender.py
"""

import pandas as pd
import os

PROC = 'data/processed'

def load_data():
    fm   = pd.read_csv(f'{PROC}/01_fund_master.csv')
    perf = pd.read_csv(f'{PROC}/07_scheme_performance.csv')
    return fm, perf

def recommend_funds(risk_appetite: str, fm: pd.DataFrame,
                    perf: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    risk_map = {
        'Low'     : ['Low'],
        'Moderate': ['Moderate', 'Moderately High'],
        'High'    : ['High', 'Very High'],
    }

    appetite = risk_appetite.strip().title()
    if appetite not in risk_map:
        print(f"\nInvalid input '{risk_appetite}'.")
        print("Please choose from: Low, Moderate, High")
        return pd.DataFrame()

    matching_grades = risk_map[appetite]

    # Filter performance data by risk grade
    filtered = perf[perf['risk_grade'].isin(matching_grades)].copy()

    # Drop duplicate columns before merge
    filtered = filtered.drop(
        columns=['fund_house', 'plan', 'expense_ratio_pct', 'category'],
        errors='ignore'
    )

    # Merge with fund master
    filtered = filtered.merge(
        fm[['amfi_code','fund_house','sub_category','plan','expense_ratio_pct']],
        on='amfi_code', how='left'
    )

    # Rank by Sharpe ratio
    top_funds = filtered.nlargest(top_n, 'sharpe_ratio')[[
        'scheme_name','fund_house','sub_category','plan',
        'sharpe_ratio','return_3yr_pct','expense_ratio_pct',
        'risk_grade','aum_crore'
    ]].reset_index(drop=True)
    top_funds.index = top_funds.index + 1

    return top_funds


def print_recommendation(risk_appetite: str, result: pd.DataFrame):
    sep = "=" * 65
    print(f"\n{sep}")
    print(f"  FUND RECOMMENDATION — {risk_appetite.upper()} RISK APPETITE")
    print(sep)
    if result.empty:
        print("  No funds found for this risk appetite.")
        return
    for i, row in result.iterrows():
        print(f"\n  #{i}  {row['scheme_name']}")
        print(f"      Fund House     : {row['fund_house']}")
        print(f"      Sub-Category   : {row['sub_category']}")
        print(f"      Plan           : {row['plan']}")
        print(f"      Sharpe Ratio   : {row['sharpe_ratio']:.3f}")
        print(f"      3yr Return     : {row['return_3yr_pct']:.2f}%")
        print(f"      Expense Ratio  : {row['expense_ratio_pct']:.2f}%")
        print(f"      Risk Grade     : {row['risk_grade']}")
        print(f"      AUM (Cr)       : Rs {row['aum_crore']:,.0f}")
    print(f"\n{sep}")


def main():
    print("\nBluestock Mutual Fund Recommender")
    print("=" * 65)

    if not os.path.exists(f'{PROC}/01_fund_master.csv'):
        print(f"ERROR: data not found at '{PROC}/'")
        print("Make sure you run this script from the project root.")
        return

    fm, perf = load_data()

    print("\nEnter your risk appetite to get personalised fund recommendations.")
    print("Options: Low / Moderate / High")
    print("Type 'all' to see recommendations for all risk levels.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("Enter risk appetite: ").strip()

        if user_input.lower() == 'quit':
            print("\nThank you for using Bluestock Fund Recommender!")
            break
        elif user_input.lower() == 'all':
            for appetite in ['Low', 'Moderate', 'High']:
                result = recommend_funds(appetite, fm, perf)
                print_recommendation(appetite, result)
        else:
            result = recommend_funds(user_input, fm, perf)
            print_recommendation(user_input, result)

        print("\n")


if __name__ == "__main__":
    main()