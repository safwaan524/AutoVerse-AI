#!/usr/bin/env python3
"""Idempotently import supplemental CSV and JSON files into a separate SQLite DB."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
BUNDLE_ROOT = PROJECT_ROOT / "AutoVerse_Supplemental_Datasets"
DEFAULT_RAW_DIR = BUNDLE_ROOT / "raw"
DEFAULT_MANIFEST = BUNDLE_ROOT / "manifest.json"
DEFAULT_DB_PATH = PROJECT_ROOT / "autoverse_supplemental.db"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "autoverse_supplemental_import_report.json"

CAR_SOURCE_FILES = ("cars_ds_final.csv", "cars_ds_final_2021.csv")
USED_PRIMARY_FILE = "UsedCars_Combined.csv"
USED_SCORE_FILE = "Dataset.csv"
USED_CITY_FILES = (
    "UsedCars_Banglore.csv",
    "UsedCars_Chennai.csv",
    "UsedCars_Delhi.csv",
    "UsedCars_Hyderabad.csv",
    "UsedCars_Kolkata.csv",
    "UsedCars_Mumbai.csv",
    "UsedCars_Pune.csv",
)
STRUCTURED_CAR_FILE = "structured_car_data_cleaned.json"
STRUCTURED_BIKE_FILE = "structured_bike_data_cleaned.json"
SUPPORTED_FILES = (
    *CAR_SOURCE_FILES,
    USED_PRIMARY_FILE,
    USED_SCORE_FILE,
    *USED_CITY_FILES,
    STRUCTURED_CAR_FILE,
    STRUCTURED_BIKE_FILE,
)

CAR_TYPED_COLUMNS = (
    "Ex-Showroom_Price",
    "Displacement",
    "Cylinders",
    "Doors",
    "City_Mileage",
    "Highway_Mileage",
    "ARAI_Certified_Mileage",
    "ARAI_Certified_Mileage_for_CNG",
    "Kerb_Weight",
    "Ground_Clearance",
    "Seating_Capacity",
    "Wheelbase",
    "Length",
    "Width",
    "Height",
    "Power",
    "Torque",
)
SCORE_NUMERIC_COLUMNS = (
    "year",
    "price",
    "distance_travelled(kms)",
    "brand_rank",
    "car_age",
    "distance below 30k km",
    "new and less used",
    "inv_car_price",
    "inv_car_dist",
    "inv_car_age",
    "inv_brand",
    "std_invprice",
    "std_invdistance_travelled",
    "std_invrank",
    "best_buy1",
    "best_buy2",
)

CITY_FILENAME_LABELS = {
    "UsedCars_Banglore.csv": "Bangalore",
    "UsedCars_Chennai.csv": "Chennai",
    "UsedCars_Delhi.csv": "Delhi",
    "UsedCars_Hyderabad.csv": "Hyderabad",
    "UsedCars_Kolkata.csv": "Kolkata",
    "UsedCars_Mumbai.csv": "Mumbai",
    "UsedCars_Pune.csv": "Pune",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().casefold())


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?", raw)
    if not match:
        return None
    try:
        return Decimal(match.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def decimal_storage(value: Decimal | None) -> str | None:
    if value is None or not value.is_finite():
        return None
    return format(value, "f")


def decimal_fingerprint(value: Any) -> str:
    parsed = parse_decimal(value)
    if parsed is None:
        return normalize_text(value)
    return format(parsed.quantize(Decimal("0.01")), "f")


def integer_value(value: Any) -> int | None:
    parsed = parse_decimal(value)
    if parsed is None or not parsed.is_finite() or parsed != parsed.to_integral_value():
        return None
    try:
        return int(parsed)
    except (ValueError, OverflowError):
        return None


def normalized_car_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return tuple(normalize_text(row.get(field)) for field in ("Make", "Model", "Variant"))  # type: ignore[return-value]


def car_record_key(row: dict[str, Any], source_file: str, row_number: int) -> str:
    key = normalized_car_key(row)
    material = "\x1f".join(key) if all(key) else f"{source_file}\x1f{row_number}"
    return sha256_bytes(material.encode("utf-8"))


def used_identity_fields(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(integer_value(row.get("year")) or normalize_text(row.get("year"))),
        normalize_text(row.get("brand")),
        normalize_text(row.get("full_model_name")),
        normalize_text(row.get("model_name")),
        decimal_fingerprint(row.get("price")),
        decimal_fingerprint(row.get("distance_travelled(kms)")),
        normalize_text(row.get("fuel_type")),
        normalize_text(row.get("city")),
    )


def used_record_key(
    row: dict[str, Any], source_file: str, row_number: int
) -> str:
    identity = used_identity_fields(row)
    material = "\x1f".join(identity)
    if not all(identity):
        material = f"{material}\x1f{source_file}\x1f{row_number}"
    return sha256_bytes(material.encode("utf-8"))


def raw_row_fingerprint(source_file: str, row_number: int, row: Any) -> str:
    return sha256_bytes(compact_json([source_file, row_number, row]).encode("utf-8"))


def issue(
    issues: list[dict[str, Any]],
    *,
    source_file: str,
    source_sha256: str,
    row_number: int | None,
    field_name: str | None,
    code: str,
    severity: str,
    raw_value: Any,
    message: str,
) -> None:
    raw_text = None if raw_value is None else str(raw_value)
    issue_key = sha256_bytes(
        compact_json(
            [source_file, source_sha256, row_number, field_name, code, raw_text]
        ).encode("utf-8")
    )
    issues.append(
        {
            "issue_fingerprint": issue_key,
            "source_file": source_file,
            "source_sha256": source_sha256,
            "source_row_number": row_number,
            "field_name": field_name,
            "issue_code": code,
            "severity": severity,
            "raw_value": raw_text,
            "message": message,
        }
    )


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name} has no CSV header.")
        rows: list[dict[str, Any]] = []
        for row in reader:
            normalized: dict[str, Any] = {}
            for key, value in row.items():
                if key is None:
                    normalized["__extra_fields__"] = value
                else:
                    normalized[key] = value
            rows.append(normalized)
        return list(reader.fieldnames), rows


def read_json_rows(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, list):
        raise ValueError(f"{path.name} must contain a top-level JSON array.")
    return value


def parse_price_range(value: Any) -> tuple[Decimal | None, Decimal | None]:
    if value is None:
        return None, None
    raw = str(value).strip()
    if not raw:
        return None, None
    token_pattern = re.compile(
        r"(?P<number>[-+]?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>crore|cr|lakhs?|lacs?|lakh|lac|k)?",
        re.IGNORECASE,
    )
    tokens: list[tuple[Decimal, str | None]] = []
    for match in token_pattern.finditer(raw):
        try:
            number = Decimal(match.group("number").replace(",", ""))
        except InvalidOperation:
            continue
        if not number.is_finite():
            continue
        unit = match.group("unit")
        tokens.append((number, unit.casefold() if unit else None))
    if not tokens:
        return None, None

    def multiplier(unit: str | None) -> Decimal:
        if unit in {"crore", "cr"}:
            return Decimal(10_000_000)
        if unit in {"lakh", "lakhs", "lac", "lacs"}:
            return Decimal(100_000)
        if unit == "k":
            return Decimal(1_000)
        return Decimal(1)

    explicit = next((unit for _, unit in reversed(tokens) if unit), None)
    parsed: list[Decimal] = []
    for number, unit in tokens[:2]:
        if unit is None and explicit and abs(number) < 1000:
            unit = explicit
        parsed.append(number * multiplier(unit))
    if len(parsed) == 1:
        return parsed[0], parsed[0]
    return min(parsed), max(parsed)


def parse_measurement(value: Any) -> tuple[Decimal | None, str | None]:
    parsed = parse_decimal(value)
    if parsed is None:
        return None, None
    raw = str(value or "")
    match = re.search(
        r"\d[\d,]*(?:\.\d+)?\s*([A-Za-z][A-Za-z0-9 /.-]*)",
        raw,
    )
    unit = match.group(1).strip(" .") if match else None
    if unit and unit.casefold().startswith(("at", "rpm")):
        unit = None
    return parsed, unit


def add_issue_for_unparsed(
    issues: list[dict[str, Any]],
    *,
    source_file: str,
    source_sha256: str,
    row_number: int,
    row: dict[str, Any],
    field: str,
    parser_succeeded: bool,
) -> None:
    raw = row.get(field)
    if raw is not None and str(raw).strip() and not parser_succeeded:
        issue(
            issues,
            source_file=source_file,
            source_sha256=source_sha256,
            row_number=row_number,
            field_name=field,
            code="numeric_parse_failed",
            severity="warning",
            raw_value=raw,
            message="Non-empty source value could not be parsed; retained as raw text.",
        )


def car_parsed_fields(row: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for field in CAR_TYPED_COLUMNS:
        value, unit = parse_measurement(row.get(field))
        if field == "Ex-Showroom_Price":
            value = parse_decimal(row.get(field))
            unit = "INR" if value is not None else None
        if field in {"Cylinders", "Doors", "Seating_Capacity", "Wheelbase", "Length", "Width", "Height"}:
            integer = integer_value(row.get(field))
            value = Decimal(integer) if integer is not None else value
        parsed[field] = {
            "value": decimal_storage(value),
            "unit": unit,
            "raw": row.get(field),
        }
    return parsed


def json_catalog_fields(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    price_min, price_max = parse_price_range(row.get("price"))
    mileage_numbers = [
        Decimal(match.replace(",", ""))
        for match in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", str(row.get("mileage") or ""))
    ]
    mileage_min = min(mileage_numbers) if mileage_numbers else None
    mileage_max = max(mileage_numbers) if mileage_numbers else None
    displacement, _ = parse_measurement(row.get("cc"))
    power, power_unit = parse_measurement(row.get("power"))
    result: dict[str, Any] = {
        "price_min_inr": decimal_storage(price_min),
        "price_max_inr": decimal_storage(price_max),
        "mileage_min": decimal_storage(mileage_min),
        "mileage_max": decimal_storage(mileage_max),
        "displacement_cc": decimal_storage(displacement),
        "power_value": decimal_storage(power),
        "power_unit": power_unit,
    }
    if kind == "car":
        seats = integer_value(row.get("seats"))
        safety, _ = parse_measurement(row.get("safety"))
        result.update(
            seats=seats,
            safety_rating_stars=decimal_storage(safety),
        )
    else:
        rating, _ = parse_measurement(row.get("rating"))
        result["rating_value"] = decimal_storage(rating)
    return result


def used_source_file_role(file_name: str) -> tuple[str, str | None]:
    if file_name == USED_PRIMARY_FILE:
        return "primary", None
    return "city_reference", CITY_FILENAME_LABELS.get(file_name)


def expected_columns_for_file(file_name: str) -> tuple[str, ...]:
    if file_name in CAR_SOURCE_FILES:
        return ("Make", "Model", "Variant")
    if file_name in {USED_PRIMARY_FILE, USED_SCORE_FILE, *USED_CITY_FILES}:
        return (
            "year",
            "brand",
            "full_model_name",
            "model_name",
            "price",
            "distance_travelled(kms)",
            "fuel_type",
            "city",
        )
    return ()


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS import_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
            files_expected INTEGER NOT NULL DEFAULT 0,
            files_imported INTEGER NOT NULL DEFAULT 0,
            rows_read INTEGER NOT NULL DEFAULT 0,
            rows_inserted INTEGER NOT NULL DEFAULT 0,
            quality_issue_count INTEGER NOT NULL DEFAULT 0,
            details_json TEXT
        );
        CREATE TABLE IF NOT EXISTS source_files (
            file_name TEXT PRIMARY KEY,
            source_sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL,
            source_record_count INTEGER NOT NULL,
            imported_at TEXT NOT NULL,
            manifest_sha256 TEXT,
            manifest_matches INTEGER
        );
        CREATE TABLE IF NOT EXISTS import_file_summary (
            run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
            file_name TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL,
            rows_read INTEGER NOT NULL,
            rows_inserted INTEGER NOT NULL,
            duplicate_rows INTEGER NOT NULL DEFAULT 0,
            malformed_rows INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (run_id, file_name)
        );
        CREATE TABLE IF NOT EXISTS data_quality_issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_fingerprint TEXT NOT NULL UNIQUE,
            first_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
            last_seen_run_id INTEGER NOT NULL REFERENCES import_runs(run_id),
            source_file TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_row_number INTEGER,
            field_name TEXT,
            issue_code TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
            raw_value TEXT,
            message TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_quality_file_row
            ON data_quality_issues(source_file, source_row_number);
        CREATE INDEX IF NOT EXISTS idx_quality_code
            ON data_quality_issues(issue_code, severity);
        CREATE TABLE IF NOT EXISTS supplemental_car_specs (
            record_key TEXT PRIMARY KEY,
            make TEXT,
            model TEXT,
            variant TEXT,
            canonical_source_file TEXT NOT NULL,
            canonical_source_row INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_row_count INTEGER NOT NULL,
            fields_json TEXT NOT NULL,
            parsed_fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS supplemental_car_spec_sources (
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            record_key TEXT NOT NULL,
            make TEXT,
            model TEXT,
            variant TEXT,
            is_canonical INTEGER NOT NULL CHECK (is_canonical IN (0, 1)),
            fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            PRIMARY KEY (source_file, source_row_number)
        );
        CREATE INDEX IF NOT EXISTS idx_car_spec_source_key
            ON supplemental_car_spec_sources(record_key);
        CREATE TABLE IF NOT EXISTS supplemental_used_listings (
            record_key TEXT PRIMARY KEY,
            source_id TEXT,
            year INTEGER,
            brand TEXT,
            full_model_name TEXT,
            model_name TEXT,
            price_inr NUMERIC,
            distance_km NUMERIC,
            fuel_type TEXT,
            city TEXT,
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            source_row_count INTEGER NOT NULL,
            fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_supp_used_brand_model
            ON supplemental_used_listings(brand, model_name);
        CREATE INDEX IF NOT EXISTS idx_supp_used_city
            ON supplemental_used_listings(city);
        CREATE TABLE IF NOT EXISTS supplemental_used_listing_sources (
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            record_key TEXT,
            source_role TEXT NOT NULL,
            expected_city TEXT,
            actual_city TEXT,
            fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            PRIMARY KEY (source_file, source_row_number)
        );
        CREATE INDEX IF NOT EXISTS idx_used_listing_source_key
            ON supplemental_used_listing_sources(record_key);
        CREATE TABLE IF NOT EXISTS supplemental_used_listing_scores (
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            source_id TEXT,
            matched_record_key TEXT,
            score_fields_json TEXT NOT NULL,
            fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            PRIMARY KEY (source_file, source_row_number)
        );
        CREATE INDEX IF NOT EXISTS idx_used_scores_listing
            ON supplemental_used_listing_scores(matched_record_key);
        CREATE TABLE IF NOT EXISTS supplemental_structured_car_catalog (
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            record_key TEXT NOT NULL,
            name TEXT,
            fuel TEXT,
            transmission TEXT,
            price_raw TEXT,
            price_min_inr NUMERIC,
            price_max_inr NUMERIC,
            mileage_raw TEXT,
            mileage_min NUMERIC,
            mileage_max NUMERIC,
            cc_raw TEXT,
            displacement_cc NUMERIC,
            power_raw TEXT,
            power_value NUMERIC,
            power_unit TEXT,
            safety_raw TEXT,
            safety_rating_stars NUMERIC,
            seats_raw TEXT,
            seats INTEGER,
            type TEXT,
            fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            PRIMARY KEY (source_file, source_row_number)
        );
        CREATE INDEX IF NOT EXISTS idx_structured_cars_name
            ON supplemental_structured_car_catalog(name);
        CREATE TABLE IF NOT EXISTS supplemental_structured_bike_catalog (
            source_file TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            row_fingerprint TEXT NOT NULL,
            record_key TEXT NOT NULL,
            brand TEXT,
            name TEXT,
            price_raw TEXT,
            price_min_inr NUMERIC,
            price_max_inr NUMERIC,
            rating_raw TEXT,
            rating_value NUMERIC,
            mileage_raw TEXT,
            mileage_min NUMERIC,
            mileage_max NUMERIC,
            cc_raw TEXT,
            displacement_cc NUMERIC,
            power_raw TEXT,
            power_value NUMERIC,
            power_unit TEXT,
            type TEXT,
            fields_json TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            PRIMARY KEY (source_file, source_row_number)
        );
        CREATE INDEX IF NOT EXISTS idx_structured_bikes_name
            ON supplemental_structured_bike_catalog(name);
        """
    )


def manifest_metadata(manifest_path: Path) -> dict[str, dict[str, Any]]:
    if not manifest_path.exists():
        return {}
    with manifest_path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, list):
        raise ValueError("Supplemental manifest must be a JSON array.")
    return {
        entry["file"]: entry
        for entry in value
        if isinstance(entry, dict) and isinstance(entry.get("file"), str)
    }


def insert_quality_issues(
    connection: sqlite3.Connection, run_id: int, issues: Iterable[dict[str, Any]]
) -> None:
    for item in issues:
        connection.execute(
            """
            INSERT INTO data_quality_issues (
                issue_fingerprint, first_run_id, last_seen_run_id, source_file,
                source_sha256, source_row_number, field_name, issue_code,
                severity, raw_value, message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(issue_fingerprint) DO UPDATE SET
                last_seen_run_id = excluded.last_seen_run_id,
                message = excluded.message
            """,
            (
                item["issue_fingerprint"],
                run_id,
                run_id,
                item["source_file"],
                item["source_sha256"],
                item["source_row_number"],
                item["field_name"],
                item["issue_code"],
                item["severity"],
                item["raw_value"],
                item["message"],
            ),
        )


def register_file(
    connection: sqlite3.Connection,
    *,
    file_name: str,
    path: Path,
    source_hash: str,
    manifest_entry: dict[str, Any] | None,
    imported_at: str,
    source_record_count: int,
) -> bool | None:
    manifest_hash = manifest_entry.get("sha256") if manifest_entry else None
    manifest_matches = (
        source_hash == manifest_hash if isinstance(manifest_hash, str) else None
    )
    connection.execute(
        """
        INSERT INTO source_files (
            file_name, source_sha256, byte_size, source_record_count,
            imported_at, manifest_sha256, manifest_matches
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_name) DO UPDATE SET
            source_sha256 = excluded.source_sha256,
            byte_size = excluded.byte_size,
            source_record_count = excluded.source_record_count,
            imported_at = excluded.imported_at,
            manifest_sha256 = excluded.manifest_sha256,
            manifest_matches = excluded.manifest_matches
        """,
        (
            file_name,
            source_hash,
            path.stat().st_size,
            source_record_count,
            imported_at,
            manifest_hash,
            None if manifest_matches is None else int(manifest_matches),
        ),
    )
    return manifest_matches


def validate_required_fields(
    issues: list[dict[str, Any]],
    *,
    source_file: str,
    source_hash: str,
    rows: list[dict[str, Any]],
) -> None:
    required = expected_columns_for_file(source_file)
    for row_number, row in enumerate(rows, start=1):
        if "__extra_fields__" in row:
            issue(
                issues,
                source_file=source_file,
                source_sha256=source_hash,
                row_number=row_number,
                field_name=None,
                code="extra_csv_fields",
                severity="warning",
                raw_value=row.get("__extra_fields__"),
                message="CSV row has more cells than the header; extra cells were retained.",
            )
        for field in required:
            if field not in row:
                issue(
                    issues,
                    source_file=source_file,
                    source_sha256=source_hash,
                    row_number=row_number,
                    field_name=field,
                    code="source_column_missing",
                    severity="error",
                    raw_value=None,
                    message="Expected source column is absent; no value was inferred.",
                )
            elif row.get(field) is None or not str(row.get(field)).strip():
                issue(
                    issues,
                    source_file=source_file,
                    source_sha256=source_hash,
                    row_number=row_number,
                    field_name=field,
                    code="required_value_missing",
                    severity="warning",
                    raw_value=row.get(field),
                    message="Required identity field is empty; retained as missing.",
                )


def import_car_specs(
    connection: sqlite3.Connection,
    *,
    source_rows: dict[str, list[dict[str, Any]]],
    hashes: dict[str, str],
    imported_at: str,
    issues: list[dict[str, Any]],
) -> dict[str, int]:
    preferred_order = {"cars_ds_final.csv": 0, "cars_ds_final_2021.csv": 1}
    grouped: dict[str, list[tuple[str, int, dict[str, Any]]]] = defaultdict(list)
    all_rows = 0
    for file_name in CAR_SOURCE_FILES:
        rows = source_rows[file_name]
        source_hash = hashes[file_name]
        for row_number, row in enumerate(rows, start=1):
            all_rows += 1
            record_key = car_record_key(row, file_name, row_number)
            grouped[record_key].append((file_name, row_number, row))

    canonical_count = 0
    duplicates = 0
    for record_key, records in grouped.items():
        ordered = sorted(
            records,
            key=lambda item: (
                preferred_order.get(item[0], 99),
                item[1],
            ),
        )
        canonical_file, canonical_row, canonical = ordered[0]
        make = canonical.get("Make")
        model = canonical.get("Model")
        variant = canonical.get("Variant")
        parsed_fields = car_parsed_fields(canonical)
        for field in ("Make", "Model", "Variant"):
            if canonical.get(field) is not None and not str(canonical.get(field)).strip():
                issue(
                    issues,
                    source_file=canonical_file,
                    source_sha256=hashes[canonical_file],
                    row_number=canonical_row,
                    field_name=field,
                    code="car_identity_blank",
                    severity="warning",
                    raw_value=canonical.get(field),
                    message="Car identity field is blank; source row retained without deduping on an incomplete key.",
                )
        for field in ("Ex-Showroom_Price", "Displacement", "ARAI_Certified_Mileage"):
            add_issue_for_unparsed(
                issues,
                source_file=canonical_file,
                source_sha256=hashes[canonical_file],
                row_number=canonical_row,
                row=canonical,
                field=field,
                parser_succeeded=parsed_fields[field]["value"] is not None,
            )
        connection.execute(
            """
            INSERT INTO supplemental_car_specs (
                record_key, make, model, variant, canonical_source_file,
                canonical_source_row, source_sha256, source_row_count,
                fields_json, parsed_fields_json, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_key,
                make,
                model,
                variant,
                canonical_file,
                canonical_row,
                hashes[canonical_file],
                len(records),
                compact_json(canonical),
                compact_json(parsed_fields),
                imported_at,
            ),
        )
        canonical_count += 1
        duplicates += len(records) - 1
        row_signatures = {
            compact_json(record[2])
            for record in records
        }
        if len(row_signatures) > 1:
            issue(
                issues,
                source_file=canonical_file,
                source_sha256=hashes[canonical_file],
                row_number=canonical_row,
                field_name="Make,Model,Variant",
                code="conflicting_duplicate_car_spec",
                severity="warning",
                raw_value=f"{len(row_signatures)} distinct source rows",
                message="Multiple source rows share a normalized car identity but contain different specifications; preferred-source policy selected the canonical row and all source rows were retained.",
            )

    for record_key, records in grouped.items():
        canonical_record = min(
            records,
            key=lambda item: (
                preferred_order.get(item[0], 99),
                item[1],
            ),
        )
        for file_name, row_number, row in records:
            row_fingerprint = raw_row_fingerprint(file_name, row_number, row)
            connection.execute(
                """
                INSERT INTO supplemental_car_spec_sources (
                    source_file, source_row_number, source_sha256, row_fingerprint,
                    record_key, make, model, variant, is_canonical, fields_json,
                    imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_name,
                    row_number,
                    hashes[file_name],
                    row_fingerprint,
                    record_key,
                    row.get("Make"),
                    row.get("Model"),
                    row.get("Variant"),
                    int((file_name, row_number) == canonical_record[:2]),
                    compact_json(row),
                    imported_at,
                ),
            )
    return {
        "source_rows": all_rows,
        "canonical_rows": canonical_count,
        "duplicate_rows": duplicates,
    }


def import_used_listings(
    connection: sqlite3.Connection,
    *,
    source_rows: dict[str, list[dict[str, Any]]],
    hashes: dict[str, str],
    imported_at: str,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    primary_rows = source_rows[USED_PRIMARY_FILE]
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for row_number, row in enumerate(primary_rows, start=1):
        grouped[used_record_key(row, USED_PRIMARY_FILE, row_number)].append(
            (row_number, row)
        )

    primary_id_to_key: dict[str, str] = {}
    for record_key, records in grouped.items():
        row_number, row = records[0]
        for source_row_number, source_row in records:
            source_id = source_row.get("Id")
            if source_id:
                if source_id in primary_id_to_key:
                    issue(
                        issues,
                        source_file=USED_PRIMARY_FILE,
                        source_sha256=hashes[USED_PRIMARY_FILE],
                        row_number=source_row_number,
                        field_name="Id",
                        code="duplicate_used_listing_id",
                        severity="warning",
                        raw_value=source_id,
                        message="Duplicate source listing ID; the source row is retained, and canonical data uses its normalized listing fingerprint.",
                    )
                else:
                    primary_id_to_key[source_id] = record_key
        connection.execute(
            """
            INSERT INTO supplemental_used_listings (
                record_key, source_id, year, brand, full_model_name, model_name,
                price_inr, distance_km, fuel_type, city, source_file,
                source_row_number, source_sha256, source_row_count, fields_json,
                imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_key,
                row.get("Id"),
                integer_value(row.get("year")),
                row.get("brand"),
                row.get("full_model_name"),
                row.get("model_name"),
                decimal_storage(parse_decimal(row.get("price"))),
                decimal_storage(parse_decimal(row.get("distance_travelled(kms)"))),
                row.get("fuel_type"),
                row.get("city"),
                USED_PRIMARY_FILE,
                row_number,
                hashes[USED_PRIMARY_FILE],
                len(records),
                compact_json(row),
                imported_at,
            ),
        )
        for field, raw_value, parsed in (
            ("year", row.get("year"), integer_value(row.get("year"))),
            ("price", row.get("price"), parse_decimal(row.get("price"))),
            (
                "distance_travelled(kms)",
                row.get("distance_travelled(kms)"),
                parse_decimal(row.get("distance_travelled(kms)")),
            ),
        ):
            add_issue_for_unparsed(
                issues,
                source_file=USED_PRIMARY_FILE,
                source_sha256=hashes[USED_PRIMARY_FILE],
                row_number=row_number,
                row=row,
                field=field,
                parser_succeeded=parsed is not None,
            )
            numeric = parse_decimal(raw_value)
            if numeric is not None and numeric < 0:
                issue(
                    issues,
                    source_file=USED_PRIMARY_FILE,
                    source_sha256=hashes[USED_PRIMARY_FILE],
                    row_number=row_number,
                    field_name=field,
                    code="negative_numeric_value",
                    severity="warning",
                    raw_value=raw_value,
                    message="Negative value retained as reported; review before analytical use.",
                )
        if len(records) > 1:
            issue(
                issues,
                source_file=USED_PRIMARY_FILE,
                source_sha256=hashes[USED_PRIMARY_FILE],
                row_number=row_number,
                field_name="listing_identity",
                code="duplicate_used_listing",
                severity="info",
                raw_value=f"{len(records)} matching source rows",
                message="Repeated listing identity collapsed in canonical inventory; every source row remains in the source audit table.",
            )

    unmatched_city_rows = 0
    city_summary: dict[str, dict[str, Any]] = {}
    source_files = (USED_PRIMARY_FILE, *USED_CITY_FILES)
    for file_name in source_files:
        rows = source_rows[file_name]
        role, expected_city = used_source_file_role(file_name)
        actual_counts: Counter[str] = Counter()
        mismatch_rows = 0
        matched_rows = 0
        for row_number, row in enumerate(rows, start=1):
            record_key = used_record_key(row, file_name, row_number)
            actual_city = (row.get("city") or "").strip()
            actual_counts[actual_city] += 1
            if role == "primary":
                matched_key = record_key
            else:
                matched_key = record_key if record_key in grouped else None
                if matched_key:
                    matched_rows += 1
                else:
                    unmatched_city_rows += 1
                    issue(
                        issues,
                        source_file=file_name,
                        source_sha256=hashes[file_name],
                        row_number=row_number,
                        field_name="listing_identity",
                        code="city_reference_not_in_primary",
                        severity="warning",
                        raw_value=actual_city,
                        message="City-file row did not match a normalized primary combined listing and was kept as reference-only, not added to inventory.",
                    )
            normalized_actual = normalize_text(actual_city)
            normalized_expected = normalize_text(expected_city)
            if role == "city_reference" and normalized_actual != normalized_expected:
                mismatch_rows += 1
                code = (
                    "known_kolkata_city_label_mismatch"
                    if file_name == "UsedCars_Kolkata.csv"
                    else "filename_city_mismatch"
                )
                severity = "error" if file_name == "UsedCars_Kolkata.csv" else "warning"
                issue(
                    issues,
                    source_file=file_name,
                    source_sha256=hashes[file_name],
                    row_number=row_number,
                    field_name="city",
                    code=code,
                    severity=severity,
                    raw_value=actual_city,
                    message=(
                        "Filename says Kolkata but the source row says Chennai; original city retained and no city inferred."
                        if file_name == "UsedCars_Kolkata.csv"
                        else f"Filename implies {expected_city}; actual city value differs. It may be a nearby or misattributed location; retained without correction."
                    ),
                )
            connection.execute(
                """
                INSERT INTO supplemental_used_listing_sources (
                    source_file, source_row_number, source_sha256, row_fingerprint,
                    record_key, source_role, expected_city, actual_city, fields_json,
                    imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_name,
                    row_number,
                    hashes[file_name],
                    raw_row_fingerprint(file_name, row_number, row),
                    matched_key,
                    role,
                    expected_city,
                    actual_city,
                    compact_json(row),
                    imported_at,
                ),
            )
        city_summary[file_name] = {
            "rows": len(rows),
            "expected_city": expected_city,
            "actual_city_counts": dict(actual_counts),
            "filename_city_mismatch_rows": mismatch_rows,
            "matched_primary_rows": matched_rows,
        }

    score_rows = source_rows[USED_SCORE_FILE]
    combined_by_id = {
        row.get("Id"): (row_number, row)
        for row_number, row in enumerate(primary_rows, start=1)
        if row.get("Id")
    }
    linked_score_rows = 0
    for row_number, row in enumerate(score_rows, start=1):
        source_id = row.get("Id")
        combined_match = combined_by_id.get(source_id)
        combined = combined_match[1] if combined_match else None
        matched_key: str | None = None
        if combined:
            shared_fields = (
                "year",
                "brand",
                "full_model_name",
                "model_name",
                "price",
                "distance_travelled(kms)",
                "fuel_type",
                "city",
            )
            fields_match = all(
                (
                    decimal_fingerprint(combined.get(field))
                    == decimal_fingerprint(row.get(field))
                    if field in {"year", "price", "distance_travelled(kms)"}
                    else normalize_text(combined.get(field)) == normalize_text(row.get(field))
                )
                for field in shared_fields
            )
            if fields_match:
                matched_key = used_record_key(
                    combined, USED_PRIMARY_FILE, combined_match[0]
                )
                linked_score_rows += 1
            else:
                issue(
                    issues,
                    source_file=USED_SCORE_FILE,
                    source_sha256=hashes[USED_SCORE_FILE],
                    row_number=row_number,
                    field_name="Id",
                    code="score_listing_fields_mismatch",
                    severity="error",
                    raw_value=source_id,
                    message="Source ID exists in the primary file but shared listing fields differ; score row was not linked.",
                )
        else:
            issue(
                issues,
                source_file=USED_SCORE_FILE,
                source_sha256=hashes[USED_SCORE_FILE],
                row_number=row_number,
                field_name="Id",
                code="score_listing_id_unmatched",
                severity="warning",
                raw_value=source_id,
                message="No matching primary listing ID; score row retained unlinked.",
            )
        parsed_scores = {
            field: decimal_storage(parse_decimal(row.get(field)))
            for field in SCORE_NUMERIC_COLUMNS
        }
        for field in ("year", "price", "distance_travelled(kms)"):
            add_issue_for_unparsed(
                issues,
                source_file=USED_SCORE_FILE,
                source_sha256=hashes[USED_SCORE_FILE],
                row_number=row_number,
                row=row,
                field=field,
                parser_succeeded=parsed_scores[field] is not None,
            )
        connection.execute(
            """
            INSERT INTO supplemental_used_listing_scores (
                source_file, source_row_number, source_sha256, row_fingerprint,
                source_id, matched_record_key, score_fields_json, fields_json,
                imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                USED_SCORE_FILE,
                row_number,
                hashes[USED_SCORE_FILE],
                raw_row_fingerprint(USED_SCORE_FILE, row_number, row),
                source_id,
                matched_key,
                compact_json(parsed_scores),
                compact_json(row),
                imported_at,
            ),
        )
    return {
        "primary_source_rows": len(primary_rows),
        "canonical_rows": len(grouped),
        "duplicate_rows": len(primary_rows) - len(grouped),
        "score_rows": len(score_rows),
        "linked_score_rows": linked_score_rows,
        "unmatched_city_reference_rows": unmatched_city_rows,
        "city_sources": city_summary,
    }


def import_structured_catalog(
    connection: sqlite3.Connection,
    *,
    file_name: str,
    kind: str,
    rows: list[Any],
    source_hash: str,
    imported_at: str,
    issues: list[dict[str, Any]],
) -> int:
    table = (
        "supplemental_structured_car_catalog"
        if kind == "car"
        else "supplemental_structured_bike_catalog"
    )
    inserted = 0
    for row_number, raw_row in enumerate(rows, start=1):
        if not isinstance(raw_row, dict):
            issue(
                issues,
                source_file=file_name,
                source_sha256=source_hash,
                row_number=row_number,
                field_name=None,
                code="json_record_not_object",
                severity="error",
                raw_value=compact_json(raw_row),
                message="JSON catalog record is not an object; it was not coerced into a vehicle.",
            )
            continue

        parsed = json_catalog_fields(kind, raw_row)
        raw_fields = compact_json(raw_row)
        record_key = sha256_bytes(
            (normalize_text(raw_row.get("name")) + "\x1f" + raw_fields).encode("utf-8")
        )
        price_min, price_max = parse_price_range(raw_row.get("price"))
        mileage_values = re.findall(
            r"[-+]?\d[\d,]*(?:\.\d+)?", str(raw_row.get("mileage") or "")
        )
        for field, succeeded in (
            ("price", price_min is not None),
            ("mileage", bool(mileage_values)),
            ("cc", parsed["displacement_cc"] is not None),
            ("power", parsed["power_value"] is not None),
        ):
            add_issue_for_unparsed(
                issues,
                source_file=file_name,
                source_sha256=source_hash,
                row_number=row_number,
                row=raw_row,
                field=field,
                parser_succeeded=succeeded,
            )
        if not str(raw_row.get("name") or "").strip():
            issue(
                issues,
                source_file=file_name,
                source_sha256=source_hash,
                row_number=row_number,
                field_name="name",
                code="catalog_name_missing",
                severity="warning",
                raw_value=raw_row.get("name"),
                message="Catalog entry has no name; raw entry retained.",
            )

        common = (
            file_name,
            row_number,
            source_hash,
            raw_row_fingerprint(file_name, row_number, raw_row),
            record_key,
        )
        if kind == "car":
            connection.execute(
                f"""
                INSERT INTO {table} (
                    source_file, source_row_number, source_sha256, row_fingerprint,
                    record_key, name, fuel, transmission, price_raw, price_min_inr,
                    price_max_inr, mileage_raw, mileage_min, mileage_max, cc_raw,
                    displacement_cc, power_raw, power_value, power_unit, safety_raw,
                    safety_rating_stars, seats_raw, seats, type, fields_json,
                    imported_at
                ) VALUES ({",".join("?" for _ in range(26))})
                """,
                common
                + (
                    raw_row.get("name"),
                    raw_row.get("fuel"),
                    raw_row.get("transmission"),
                    raw_row.get("price"),
                    decimal_storage(price_min),
                    decimal_storage(price_max),
                    raw_row.get("mileage"),
                    parsed["mileage_min"],
                    parsed["mileage_max"],
                    raw_row.get("cc"),
                    parsed["displacement_cc"],
                    raw_row.get("power"),
                    parsed["power_value"],
                    parsed["power_unit"],
                    raw_row.get("safety"),
                    parsed["safety_rating_stars"],
                    None if raw_row.get("seats") is None else str(raw_row.get("seats")),
                    parsed["seats"],
                    raw_row.get("type"),
                    raw_fields,
                    imported_at,
                ),
            )
        else:
            connection.execute(
                f"""
                INSERT INTO {table} (
                    source_file, source_row_number, source_sha256, row_fingerprint,
                    record_key, brand, name, price_raw, price_min_inr, price_max_inr,
                    rating_raw, rating_value, mileage_raw, mileage_min, mileage_max,
                    cc_raw, displacement_cc, power_raw, power_value, power_unit, type,
                    fields_json, imported_at
                ) VALUES ({",".join("?" for _ in range(23))})
                """,
                common
                + (
                    raw_row.get("brand"),
                    raw_row.get("name"),
                    raw_row.get("price"),
                    decimal_storage(price_min),
                    decimal_storage(price_max),
                    raw_row.get("rating"),
                    parsed["rating_value"],
                    raw_row.get("mileage"),
                    parsed["mileage_min"],
                    parsed["mileage_max"],
                    raw_row.get("cc"),
                    parsed["displacement_cc"],
                    raw_row.get("power"),
                    parsed["power_value"],
                    parsed["power_unit"],
                    raw_row.get("type"),
                    raw_fields,
                    imported_at,
                ),
            )
        inserted += 1
    return inserted


def expected_role(file_name: str) -> str:
    if file_name in CAR_SOURCE_FILES:
        return "car_spec_source"
    if file_name == USED_PRIMARY_FILE:
        return "primary_used_listings"
    if file_name == USED_SCORE_FILE:
        return "supplementary_used_scoring"
    if file_name in USED_CITY_FILES:
        return "city_reference_only"
    if file_name == STRUCTURED_CAR_FILE:
        return "structured_car_catalog"
    if file_name == STRUCTURED_BIKE_FILE:
        return "structured_bike_catalog"
    return "unclassified"


def table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    names = (
        "source_files",
        "supplemental_car_specs",
        "supplemental_car_spec_sources",
        "supplemental_used_listings",
        "supplemental_used_listing_sources",
        "supplemental_used_listing_scores",
        "supplemental_structured_car_catalog",
        "supplemental_structured_bike_catalog",
        "data_quality_issues",
    )
    return {
        name: int(connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
        for name in names
    }


def import_supplemental_data(
    raw_dir: Path = DEFAULT_RAW_DIR,
    database_path: Path = DEFAULT_DB_PATH,
    manifest_path: Path = DEFAULT_MANIFEST,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Raw dataset directory not found: {raw_dir}")
    missing = [file_name for file_name in SUPPORTED_FILES if not (raw_dir / file_name).is_file()]
    if missing:
        raise FileNotFoundError(f"Required supplemental dataset files are missing: {missing}")

    manifest = manifest_metadata(manifest_path)
    if not manifest:
        raise FileNotFoundError(f"Supplemental manifest not found or empty: {manifest_path}")
    manifest_files = set(manifest)
    raw_files = {
        path.name
        for path in raw_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".csv", ".json"}
    }
    if manifest_files != set(SUPPORTED_FILES):
        raise ValueError(
            "Manifest file list does not match the importer's supported dataset list: "
            f"missing={sorted(set(SUPPORTED_FILES) - manifest_files)}, "
            f"unsupported={sorted(manifest_files - set(SUPPORTED_FILES))}"
        )
    if raw_files != set(SUPPORTED_FILES):
        raise ValueError(
            "Raw CSV/JSON file list does not match the importer's supported dataset list: "
            f"missing={sorted(set(SUPPORTED_FILES) - raw_files)}, "
            f"unhandled={sorted(raw_files - set(SUPPORTED_FILES))}"
        )
    imported_at = utc_now()
    hashes = {name: sha256_file(raw_dir / name) for name in SUPPORTED_FILES}
    csv_names = (*CAR_SOURCE_FILES, USED_PRIMARY_FILE, USED_SCORE_FILE, *USED_CITY_FILES)
    source_rows: dict[str, list[dict[str, Any]]] = {}
    source_headers: dict[str, list[str]] = {}
    json_rows: dict[str, list[Any]] = {}
    for file_name in csv_names:
        headers, rows = read_csv_rows(raw_dir / file_name)
        source_headers[file_name] = headers
        source_rows[file_name] = rows
    json_rows[STRUCTURED_CAR_FILE] = read_json_rows(raw_dir / STRUCTURED_CAR_FILE)
    json_rows[STRUCTURED_BIKE_FILE] = read_json_rows(raw_dir / STRUCTURED_BIKE_FILE)

    issues: list[dict[str, Any]] = []
    for file_name, rows in source_rows.items():
        validate_required_fields(
            issues,
            source_file=file_name,
            source_hash=hashes[file_name],
            rows=rows,
        )
        if file_name in CAR_SOURCE_FILES and "Make" not in source_headers[file_name]:
            issue(
                issues,
                source_file=file_name,
                source_sha256=hashes[file_name],
                row_number=None,
                field_name="Make",
                code="car_source_header_missing",
                severity="error",
                raw_value=None,
                message="Car specification identity header is missing.",
            )
        if file_name == USED_SCORE_FILE:
            for field in SCORE_NUMERIC_COLUMNS:
                if field not in source_headers[file_name]:
                    issue(
                        issues,
                        source_file=file_name,
                        source_sha256=hashes[file_name],
                        row_number=None,
                        field_name=field,
                        code="score_source_column_missing",
                        severity="warning",
                        raw_value=None,
                        message="Scoring field is absent from the source header.",
                    )

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    run_started = utc_now()
    run_id = 0
    report: dict[str, Any] = {}
    try:
        create_schema(connection)
        with connection:
            run_cursor = connection.execute(
                """
                INSERT INTO import_runs (
                    started_at, status, files_expected
                ) VALUES (?, 'running', ?)
                """,
                (run_started, len(SUPPORTED_FILES)),
            )
            run_id = int(run_cursor.lastrowid)
            for table in (
                "supplemental_car_spec_sources",
                "supplemental_car_specs",
                "supplemental_used_listing_sources",
                "supplemental_used_listing_scores",
                "supplemental_used_listings",
                "supplemental_structured_car_catalog",
                "supplemental_structured_bike_catalog",
            ):
                connection.execute(f'DELETE FROM "{table}"')

            for file_name in SUPPORTED_FILES:
                path = raw_dir / file_name
                is_csv = file_name.lower().endswith(".csv")
                row_count = len(source_rows[file_name]) if is_csv else len(json_rows[file_name])
                match = register_file(
                    connection,
                    file_name=file_name,
                    path=path,
                    source_hash=hashes[file_name],
                    manifest_entry=manifest.get(file_name),
                    imported_at=imported_at,
                    source_record_count=row_count,
                )
                manifest_entry = manifest.get(file_name)
                if manifest_entry is None:
                    issue(
                        issues,
                        source_file=file_name,
                        source_sha256=hashes[file_name],
                        row_number=None,
                        field_name=None,
                        code="manifest_entry_missing",
                        severity="warning",
                        raw_value=None,
                        message="File is imported but has no matching manifest entry.",
                    )
                elif match is False:
                    issue(
                        issues,
                        source_file=file_name,
                        source_sha256=hashes[file_name],
                        row_number=None,
                        field_name=None,
                        code="manifest_hash_mismatch",
                        severity="error",
                        raw_value=hashes[file_name],
                        message="Source file SHA-256 differs from the manifest; imported bytes were retained and reported without modifying the source.",
                    )

            car_stats = import_car_specs(
                connection,
                source_rows=source_rows,
                hashes=hashes,
                imported_at=imported_at,
                issues=issues,
            )
            used_stats = import_used_listings(
                connection,
                source_rows=source_rows,
                hashes=hashes,
                imported_at=imported_at,
                issues=issues,
            )
            json_inserted = {
                STRUCTURED_CAR_FILE: import_structured_catalog(
                    connection,
                    file_name=STRUCTURED_CAR_FILE,
                    kind="car",
                    rows=json_rows[STRUCTURED_CAR_FILE],
                    source_hash=hashes[STRUCTURED_CAR_FILE],
                    imported_at=imported_at,
                    issues=issues,
                ),
                STRUCTURED_BIKE_FILE: import_structured_catalog(
                    connection,
                    file_name=STRUCTURED_BIKE_FILE,
                    kind="bike",
                    rows=json_rows[STRUCTURED_BIKE_FILE],
                    source_hash=hashes[STRUCTURED_BIKE_FILE],
                    imported_at=imported_at,
                    issues=issues,
                ),
            }

            issue_by_file: dict[str, Counter[str]] = defaultdict(Counter)
            issue_severity_by_file: dict[str, Counter[str]] = defaultdict(Counter)
            for item in issues:
                issue_by_file[item["source_file"]][item["severity"]] += 1
                issue_severity_by_file[item["source_file"]][item["issue_code"]] += 1

            for file_name in SUPPORTED_FILES:
                is_csv = file_name.lower().endswith(".csv")
                row_count = len(source_rows[file_name]) if is_csv else len(json_rows[file_name])
                if file_name == USED_PRIMARY_FILE:
                    inserted = used_stats["canonical_rows"]
                    duplicate_rows = used_stats["duplicate_rows"]
                elif file_name in CAR_SOURCE_FILES:
                    # Individual source counts remain distinct; canonical rows are counted at the preferred file level.
                    inserted = (
                        car_stats["canonical_rows"]
                        if file_name == "cars_ds_final.csv"
                        else 0
                    )
                    duplicate_rows = max(
                        0,
                        row_count
                        - len(
                            {
                                car_record_key(row, file_name, row_number)
                                for row_number, row in enumerate(
                                    source_rows[file_name], start=1
                                )
                            }
                        ),
                    )
                elif file_name == USED_SCORE_FILE:
                    inserted = len(source_rows[file_name])
                    duplicate_rows = 0
                elif file_name in USED_CITY_FILES:
                    inserted = len(source_rows[file_name])
                    duplicate_rows = row_count - len(
                        {
                            used_record_key(row, file_name, row_number)
                            for row_number, row in enumerate(
                                source_rows[file_name], start=1
                            )
                        }
                    )
                elif file_name in json_inserted:
                    inserted = json_inserted[file_name]
                    duplicate_rows = 0
                else:
                    inserted = row_count
                    duplicate_rows = 0
                severities = issue_by_file[file_name]
                status = "warning" if severities.get("error", 0) or severities.get("warning", 0) else "ok"
                connection.execute(
                    """
                    INSERT INTO import_file_summary (
                        run_id, file_name, source_sha256, byte_size, rows_read,
                        rows_inserted, duplicate_rows, malformed_rows,
                        warning_count, error_count, role, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        file_name,
                        hashes[file_name],
                        (raw_dir / file_name).stat().st_size,
                        row_count,
                        inserted,
                        duplicate_rows,
                        sum(
                            1
                            for item in issues
                            if item["source_file"] == file_name
                            and item["issue_code"] in {
                                "extra_csv_fields",
                                "json_record_not_object",
                            }
                        ),
                        severities.get("warning", 0),
                        severities.get("error", 0),
                        expected_role(file_name),
                        status,
                    ),
                )

            insert_quality_issues(connection, run_id, issues)
            issue_summary = dict(Counter(item["severity"] for item in issues))
            issue_codes = dict(Counter(item["issue_code"] for item in issues))
            rows_read = sum(
                len(source_rows[name]) if name.lower().endswith(".csv") else len(json_rows[name])
                for name in SUPPORTED_FILES
            )
            counts = table_counts(connection)
            report = {
                "run_id": run_id,
                "status": "completed",
                "started_at": run_started,
                "completed_at": utc_now(),
                "database": str(database_path),
                "raw_directory": str(raw_dir),
                "files_expected": len(SUPPORTED_FILES),
                "files_imported": len(SUPPORTED_FILES),
                "rows_read": rows_read,
                "car_spec_deduplication": car_stats,
                "used_listing_deduplication": used_stats,
                "structured_catalog_rows": json_inserted,
                "quality_issues_this_run": {
                    "by_severity": issue_summary,
                    "by_code": issue_codes,
                },
                "table_counts": counts,
                "city_attribution_audit": used_stats["city_sources"],
            }
            connection.execute(
                """
                UPDATE import_runs
                SET completed_at = ?, status = 'completed', files_imported = ?,
                    rows_read = ?, rows_inserted = ?, quality_issue_count = ?,
                    details_json = ?
                WHERE run_id = ?
                """,
                (
                    report["completed_at"],
                    len(SUPPORTED_FILES),
                    rows_read,
                    sum(counts.values()),
                    len(issues),
                    compact_json(report),
                    run_id,
                ),
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    except Exception as exc:
        connection.rollback()
        if run_id:
            with connection:
                connection.execute(
                    """
                    UPDATE import_runs
                    SET completed_at = ?, status = 'failed', details_json = ?
                    WHERE run_id = ?
                    """,
                    (
                        utc_now(),
                        compact_json({"error": str(exc)}),
                        run_id,
                    ),
                )
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    try:
        report = import_supplemental_data(
            raw_dir=args.raw_dir,
            database_path=args.database,
            manifest_path=args.manifest,
            report_path=args.report,
        )
    except Exception as exc:
        print(f"Supplemental import failed: {exc}", file=sys.stderr)
        return 1

    print("AUTOVERSE SUPPLEMENTAL IMPORT")
    print(f"Database: {report['database']}")
    print(f"Report: {args.report}")
    print(
        f"Run {report['run_id']}: {report['files_imported']}/"
        f"{report['files_expected']} files, {report['rows_read']} source rows"
    )
    print("Table counts:")
    for table, count in report["table_counts"].items():
        print(f"  {table}: {count:,}")
    print("Quality issues:")
    for severity, count in report["quality_issues_this_run"]["by_severity"].items():
        print(f"  {severity}: {count:,}")
    if report["quality_issues_this_run"]["by_code"]:
        print("Issue codes:")
        for code, count in sorted(
            report["quality_issues_this_run"]["by_code"].items()
        ):
            print(f"  {code}: {count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
