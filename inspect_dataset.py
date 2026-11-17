
import pandas as pd
from pathlib import Path

base = Path("datasets/tco-india")

# Locate the relevant Parquet files
for file in base.rglob("*.parquet"):
    name = file.stem.lower()

    if name in ["brands", "models", "variants", "prices"]:
        df = pd.read_parquet(file)

        print("\n", "=" * 55)
        print("FILE:", name)

        # Search all text columns for BMW
        text_cols = df.select_dtypes(include="object").columns

        for col in text_cols:
            matches = df[
                df[col].astype(str).str.contains(
                    "BMW", case=False, na=False
                )
            ]

            if not matches.empty:
                print(f"\nBMW found in column: {col}")
                print(matches.head(10).to_string(index=False))

        if name == "models":
            print("\nMODEL COLUMNS:", df.columns.tolist())

print("\nBMW INVESTIGATION COMPLETE")


