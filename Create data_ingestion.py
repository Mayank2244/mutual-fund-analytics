import pandas as pd
import os

DATA_PATH = "data/raw"

files = [f for f in os.listdir(DATA_PATH) if f.endswith(".csv")]

for file in files:
    print("\n" + "="*60)
    print("FILE:", file)

    df = pd.read_csv(os.path.join(DATA_PATH, file))

    print("Shape:", df.shape)
    print("\nColumns:")
    print(df.columns.tolist())

    print("\nData Types:")
    print(df.dtypes)

    print("\nFirst 5 Rows:")
    print(df.head())

    print("\nMissing Values:")
    print(df.isnull().sum())