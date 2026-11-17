"""
AutoVerse AI — Central Database Access Layer
Provides cached, clean access to the SQLite vehicle database.
"""
import sqlite3
import pandas as pd
from pathlib import Path
import streamlit as st

DB_PATH = Path(__file__).parent / "autoverse.db"

BODY_STYLE_MAP = {
    1: "Hatchback",
    2: "Sedan",
    3: "SUV",
    4: "Coupe",
    5: "Convertible",
    6: "MUV / MPV",
    7: "Pickup Truck",
    8: "Crossover",
    9: "Van",
}

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(ttl=3600, show_spinner=False)
def load_vehicles() -> pd.DataFrame:
    """
    Load all variants with pricing and brand/model info.
    Returns a clean DataFrame with standardized columns.
    ~4,000 priced variants from the autoverse.db database.
    """
    query = """
        SELECT
            v.source_id                             AS vehicle_id,
            b.display_name                          AS make,
            m.display_name                          AS model,
            v.name                                  AS variant,
            v.fuel_type_name                        AS fuel_type,
            v.transmission_name                     AS transmission,
            v.engine_cc                             AS displacement_cc,
            v.mileage_kmpl                          AS mileage_kmpl,
            v.seats                                 AS seating_capacity,
            m.body_style_id                         AS body_style_id,
            MIN(p.ex_showroom_inr)                  AS price,
            MIN(p.on_road_inr)                      AS on_road_price
        FROM variants v
        JOIN models m ON v.model_source_id = m.source_id
        JOIN brands b ON m.brand_slug = b.slug
        JOIN prices p ON v.source_id = p.source_id
        WHERE p.ex_showroom_inr > 100000
          AND p.ex_showroom_inr < 100000000
        GROUP BY v.source_id
        ORDER BY b.display_name, m.display_name, v.name
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Map body style
    df["body_type"] = df["body_style_id"].map(BODY_STYLE_MAP).fillna("Other")

    # Normalize fuel type
    df["fuel_type"] = df["fuel_type"].str.strip().str.title()
    df["transmission"] = df["transmission"].str.strip().str.title()

    # Year placeholder (not in DB; use 2024)
    df["year"] = 2024

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_image_map() -> dict:
    """
    Load a mapping of model name → best image URL from used_listings.
    Returns dict: {model_name: image_url}
    """
    query = """
        SELECT model, image_url
        FROM used_listings
        WHERE image_url IS NOT NULL AND image_url != ''
        GROUP BY model
        ORDER BY model
    """
    conn = get_connection()
    rows = conn.execute(query).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


@st.cache_data(ttl=3600, show_spinner=False)
def get_stats() -> dict:
    """Return high-level statistics for the Home dashboard."""
    df = load_vehicles()
    img_map = load_image_map()
    return {
        "total_vehicles": len(df),
        "total_makes": df["make"].nunique(),
        "avg_price": df["price"].mean(),
        "min_price": df["price"].min(),
        "max_price": df["price"].max(),
        "top_fuel": df["fuel_type"].value_counts().index[0] if not df.empty else "Petrol",
        "top_body": df["body_type"].value_counts().index[0] if not df.empty else "SUV",
        "total_images": len(img_map),
    }


def get_image_url(make: str, model: str, img_map: dict = None) -> str:
    """Find the best matching image URL for a make+model."""
    FALLBACK = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/No_image_available_450_x_300.svg/450px-No_image_available_450_x_300.svg.png"

    if img_map is None:
        img_map = load_image_map()

    # Try exact model match first
    if model in img_map:
        return img_map[model]

    # Try partial / fuzzy match on model name
    model_lower = model.lower()
    for key, url in img_map.items():
        if model_lower in key.lower() or key.lower() in model_lower:
            return url

    # Try brand-only match (last resort)
    make_lower = make.lower()
    for key, url in img_map.items():
        if make_lower in key.lower():
            return url

    return FALLBACK


def search_vehicles(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Case-insensitive search across make, model, variant."""
    if not query:
        return df
    q = query.lower()
    mask = (
        df["make"].str.lower().str.contains(q, na=False) |
        df["model"].str.lower().str.contains(q, na=False) |
        df["variant"].str.lower().str.contains(q, na=False)
    )
    return df[mask]
