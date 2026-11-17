
import pandas as pd
from pathlib import Path

base = Path("datasets/tco-india")

def load_table(name):
    files = list(base.rglob(f"{name}.parquet"))
    if not files:
        print(f"{name} file not found!")
        return None
    return pd.read_parquet(files[0])

# Load tables
brands = load_table("brands")
models = load_table("models")
variants = load_table("variants")

print("\n========== AUTOVERSE VEHICLE INVENTORY ==========")

if brands is not None:
    print("\nBRANDS")
    print("Total brands:", len(brands))
    print(brands.columns.tolist())
    print(brands.head(15).to_string(index=False))

if models is not None:
    print("\nMODELS")
    print("Total models:", len(models))
    print(models.columns.tolist())
    print(models.head(20).to_string(index=False))

if variants is not None:
    print("\nVARIANTS")
    print("Total variants:", len(variants))
    print(variants.columns.tolist())
    print(variants.head(15).to_string(index=False))

print("\n========== INVENTORY COMPLETE ==========")



