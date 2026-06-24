import pandas as pd

fund = pd.read_csv("data/raw/01_fund_master.csv")
nav = pd.read_csv("data/raw/02_nav_history.csv")

master_codes = set(fund["amfi_code"])
nav_codes = set(nav["amfi_code"])

missing = master_codes - nav_codes

print("Fund Master Codes:", len(master_codes))
print("NAV History Codes:", len(nav_codes))
print("Missing Codes:", len(missing))
print(missing)