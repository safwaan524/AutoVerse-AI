# AutoVerse AI supplementary datasets

This bundle contains the original uploaded dataset files, copied without modifying their contents.

## Files and observed shapes

| File | Records | Fields |
|---|---:|---:|
| `cars_ds_final_2021.csv` | 1267 | 141 |
| `cars_ds_final.csv` | 1276 | 141 |
| `Dataset.csv` | 1725 | 23 |
| `UsedCars_Combined.csv` | 1725 | 9 |
| `UsedCars_Banglore.csv` | 247 | 9 |
| `UsedCars_Chennai.csv` | 246 | 9 |
| `UsedCars_Delhi.csv` | 246 | 9 |
| `UsedCars_Hyderabad.csv` | 245 | 9 |
| `UsedCars_Kolkata.csv` | 247 | 9 |
| `UsedCars_Mumbai.csv` | 247 | 9 |
| `UsedCars_Pune.csv` | 247 | 9 |
| `structured_bike_data_cleaned.json` | 561 | 8 |
| `structured_car_data_cleaned.json` | 504 | 10 |

## Data integration recommendations

1. Keep `autoverse.db` as the existing primary database. Back it up before any migration.
2. Do not run `build_database.py` as part of this import. Its existing implementation can replace tables.
3. Import supplemental data into new, clearly named tables or a separate attached database. Do not overwrite the existing `brands`, `models`, `variants`, `prices`, or `used_listings` tables.
4. Preserve every raw source file and original source column. Add provenance fields such as `source_file`, `imported_at`, and a stable row fingerprint in the supplemental tables.
5. Normalize into additional typed columns for filtering, but retain raw text values alongside parsed values. Missing or malformed values must remain NULL/unknown, not be fabricated.
6. Do not treat prices, ratings, mileage, or expected-launch entries in the structured JSON datasets as verified live/current facts. Display their source and date/provenance status when shown.
7. No image or 3D geometry files are included in this bundle. Vehicle images and GLB/GLTF models must be managed as separate assets with appropriate licensing and attribution.

## Important overlap and quality checks

- `cars_ds_final_2021.csv` has 1,267 rows; `cars_ds_final.csv` has 1,276 rows. Their `(Make, Model, Variant)` key check found 1,250 distinct keys in the 2021 file and 1,267 in the newer file; every older key was present in the newer file, with 17 additional distinct keys in the newer file. Do not append both as separate inventory without deduplication.
- `Dataset.csv` and `UsedCars_Combined.csv` each contain 1,725 records. `Dataset.csv` has additional engineered score/age/rank columns. Treat it as an enriched companion to the combined used-car data, not a second set of listings.
- The seven city CSVs are subsets of the combined used-car dataset when checked using normalized listing fields. Their unique row-key counts are smaller than their raw row counts because there are repeated rows.
- `UsedCars_Kolkata.csv` contains 247 rows whose `city` field is `Chennai`; verify/correct city attribution from reliable source context before using it as Kolkata inventory.
- `UsedCars_Delhi.csv` contains records for locations beyond Delhi (including Dehradun, Noida, Ghaziabad and Lucknow). `UsedCars_Mumbai.csv` also contains nearby/other locations such as Thane, Navi Mumbai and Dehradun. Filter by the actual `city` column rather than filename alone.
- JSON datasets: `structured_bike_data_cleaned.json` has 561 records and fields `brand`, `name`, `price`, `rating`, `mileage`, `cc`, `power`, `type`. `structured_car_data_cleaned.json` has 504 records and fields `name`, `price`, `fuel`, `mileage`, `transmission`, `cc`, `power`, `safety`, `seats`, `type`. Their numeric values are often stored as formatted strings; some records have missing or misaligned values.

## Suggested supplemental data model

- `supplemental_car_specs_raw`: raw rows from the two `cars_ds_final*.csv` files, with source/year metadata and a normalized `(make, model, variant)` fingerprint.
- `supplemental_used_listings_raw`: canonical raw used listings sourced from `UsedCars_Combined.csv`; use `Dataset.csv` only as a linked enrichment source keyed by `Id`/validated listing fingerprint.
- `supplemental_two_wheeler_catalog`: bike records parsed from `structured_bike_data_cleaned.json`.
- `supplemental_car_catalog`: structured car records parsed from `structured_car_data_cleaned.json`; keep expected-launch entries and incomplete records separately flagged.
- City-specific CSVs should be retained as audit/reference files, not imported as additive listings unless deduplication proves a genuinely new listing.

## Integrity

The files in `raw/` are byte-for-byte copies of the uploaded files. SHA-256 values follow.
- `cars_ds_final_2021.csv`: `6b7e33fbfcfdbcec2c7c5a403dddaa056aa0a0dc6c0c27b88cebf397337e4819`
- `cars_ds_final.csv`: `17edb832fd1e955c283f13d15de85b112603ef5ec9b9035ecc1b5793c5c77636`
- `Dataset.csv`: `6d8d8546de6d5a215d95d8e030b42a9be3cd8232055ab45d6f68afb9be02e20b`
- `UsedCars_Combined.csv`: `e59c070d80bbe2745b99e84e52e006560667221e6942a283d1012dcaefb66816`
- `UsedCars_Banglore.csv`: `f2f554fb7225525db408b5f3b0d91c7e7912053954d36be5e277b709d15b0fde`
- `UsedCars_Chennai.csv`: `500cf256eb5ef2221a37da4fb20907f687695851533274b130d389e986c8dea8`
- `UsedCars_Delhi.csv`: `addae996b4c84c46ec63e703b3d732ccdfa9b08046789e92862d16d9490908e9`
- `UsedCars_Hyderabad.csv`: `2dec3b134f228f0c74bfb88b531fb1ad9a7f722efd936c51c4079a2c92108510`
- `UsedCars_Kolkata.csv`: `d34732399386d50f45b62abbb22963cf9ad14402570139523b2cf21f4b777b8d`
- `UsedCars_Mumbai.csv`: `0247a39fed89ce55895880145611bb14a7535f44c9c57fe244ec0536281540df`
- `UsedCars_Pune.csv`: `3b8025a8fb345ac99f3759c3ed41e90395b7817197561cd781065dd59ca4db12`
- `structured_bike_data_cleaned.json`: `7442e06c65addda64c0b5ae6ff6841b4746c13209b16d7ac38a0e7b7421dc2de`
- `structured_car_data_cleaned.json`: `22409656adfab01779b77e394cd4b0c9fca717b713705cc705e7d5e78458b658`
