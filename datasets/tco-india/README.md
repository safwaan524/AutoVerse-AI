---
license: cc-by-4.0
task_categories:
  - tabular-classification
configs:
  - config_name: car_brands
    data_files:
      - split: train
        path: car/brands.parquet
  - config_name: car_models
    data_files:
      - split: train
        path: car/models.parquet
  - config_name: car_variants
    data_files:
      - split: train
        path: car/variants.parquet
  - config_name: car_prices
    data_files:
      - split: train
        path: car/prices.parquet
  - config_name: car_brand_groups
    data_files:
      - split: train
        path: car/brand_groups.parquet
  - config_name: car_cities
    data_files:
      - split: train
        path: car/cities.parquet
  - config_name: car_used_listings
    data_files:
      - split: train
        path: car/used_listings.parquet
  - config_name: fuel_prices
    data_files:
      - split: train
        path: fuel/fuel_prices.parquet
---

# TCO India — car + fuel modules

Car makes, models, variants and dated on-road prices from CarDekho and CarWale (cross-source prices validated by variant descriptor + city), plus daily fuel prices. Previously `tco-fuel` (now folded as `fuel/` module here).

| Config | File | Rows describe |
|--------|------|---------------|
| car_brands | car/brands.parquet | car brands (with ownership group + country) |
| car_models | car/models.parquet | car models |
| car_variants | car/variants.parquet | car variants (specs) |
| car_prices | car/prices.parquet | variant × city on-road price (dated) |
| car_brand_groups | car/brand_groups.parquet | brand ownership groups (ownership_pct/ownership_note) |
| car_cities | car/cities.parquet | city → state mapping |
| car_used_listings | car/used_listings.parquet | used car listings (asking price, km, year + listing link) |
| fuel_prices | fuel/fuel_prices.parquet | daily fuel prices by state/city |

License: **CC-BY-4.0** for the compilation (facts are public; presentation/joins are CC-BY). Sources: CarDekho/CarWale (car), IOCL/BPCL (fuel) — not affiliated; transformed & validated.

Each brands/model/variant row carries `source_coverage` (cardekho_only | carwale_only | both).
Read with DuckDB: `SELECT * FROM 'hf://datasets/<repo>/car/prices.parquet'`.
