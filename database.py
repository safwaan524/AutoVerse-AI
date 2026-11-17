import sqlite3
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from config import DATABASE_PATH, FORBIDDEN_SQL_KEYWORDS


def get_connection(read_only: bool = True) -> sqlite3.Connection:
    """Create a connection to the SQLite database. Read-only by default."""
    if read_only:
        uri = f"file:{DATABASE_PATH.as_posix()}?mode=ro"
        return sqlite3.connect(uri, uri=True)
    return sqlite3.connect(DATABASE_PATH)


def get_database_stats() -> Dict[str, int]:
    """Retrieve record counts for key automotive tables."""
    conn = get_connection()
    cursor = conn.cursor()
    tables = [
        "brands", "models", "variants", "prices", 
        "used_listings", "fuel_prices", "cities", "brand_groups"
    ]
    stats = {}
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            stats[table] = cursor.fetchone()[0]
        except sqlite3.Error:
            stats[table] = 0
    conn.close()
    return stats


def get_all_brands() -> List[str]:
    """Get list of distinct brand names available in models or brands table."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    SELECT DISTINCT b.name 
    FROM brands b
    JOIN models m ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
    WHERE b.name IS NOT NULL
    ORDER BY b.name ASC
    """
    cursor.execute(query)
    brands = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return brands


def get_models_by_brand(brand_name: Optional[str] = None) -> List[str]:
    """Get list of vehicle models, optionally filtered by brand name."""
    conn = get_connection()
    cursor = conn.cursor()
    if brand_name:
        query = """
        SELECT DISTINCT m.name 
        FROM models m
        JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
        WHERE b.name = ?
        ORDER BY m.name ASC
        """
        cursor.execute(query, (brand_name,))
    else:
        query = "SELECT DISTINCT name FROM models WHERE name IS NOT NULL ORDER BY name ASC"
        cursor.execute(query)
    models = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return models


def get_fuel_types() -> List[str]:
    """Get distinct fuel types from variants and used listings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT fuel_type_name FROM variants 
    WHERE fuel_type_name IS NOT NULL AND fuel_type_name != ''
    ORDER BY fuel_type_name ASC
    """)
    fuel_types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return fuel_types


def get_transmission_types() -> List[str]:
    """Get distinct transmission types from variants."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT transmission_name FROM variants 
    WHERE transmission_name IS NOT NULL AND transmission_name != ''
    ORDER BY transmission_name ASC
    """)
    transmissions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return transmissions


def get_popular_cities() -> List[str]:
    """Get popular cities for price lookup."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT city_name FROM cities 
    WHERE is_popular = 1 AND city_name IS NOT NULL
    ORDER BY city_name ASC
    """)
    cities = [row[0] for row in cursor.fetchall()]
    if not cities:
        cursor.execute("""
        SELECT DISTINCT city_name FROM prices 
        WHERE city_name IS NOT NULL 
        LIMIT 20
        """)
        cities = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cities


def search_vehicles(
    query: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    fuel_type: Optional[str] = None,
    transmission: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    city: Optional[str] = None,
    vehicle_type: str = "All",
    limit: int = 50
) -> pd.DataFrame:
    """
    Search across new vehicle models/variants and used listings.
    Returns a unified pandas DataFrame with relevant specs and prices.
    """
    conn = get_connection()
    results = []

    # 1. Search New Vehicles
    if vehicle_type in ["All", "New"]:
        conditions = ["1=1"]
        params = []

        if brand:
            conditions.append("(b.name = ? OR m.brand_slug = ?)")
            params.extend([brand, brand.lower()])
        if model:
            conditions.append("m.name LIKE ?")
            params.append(f"%{model}%")
        if fuel_type:
            conditions.append("v.fuel_type_name = ?")
            params.append(fuel_type)
        if transmission:
            conditions.append("v.transmission_name LIKE ?")
            params.append(f"%{transmission}%")
        if city:
            conditions.append("(p.city_name = ? OR p.city_name IS NULL)")
            params.append(city)
        if query:
            conditions.append(
                "(m.name LIKE ? OR b.name LIKE ? OR v.name LIKE ? OR v.key_features LIKE ?)"
            )
            q_param = f"%{query}%"
            params.extend([q_param, q_param, q_param, q_param])

        where_clause = " AND ".join(conditions)

        sql_new = f"""
        SELECT 
            b.name AS brand,
            m.name AS model,
            v.name AS variant,
            v.fuel_type_name AS fuel_type,
            v.transmission_name AS transmission,
            v.mileage_kmpl,
            v.engine_cc,
            COALESCE(p.ex_showroom_inr, 0) AS ex_showroom_inr,
            COALESCE(p.on_road_inr, 0) AS on_road_inr,
            COALESCE(p.city_name, 'National Avg') AS city,
            'New' AS vehicle_type
        FROM models m
        JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
        JOIN variants v ON v.model_source_id = m.source_id
        LEFT JOIN (
            SELECT model_name, variant_name, city_name, 
                   MIN(ex_showroom_inr) as ex_showroom_inr, 
                   MIN(on_road_inr) as on_road_inr
            FROM prices
            GROUP BY model_name, variant_name
        ) p ON p.model_name = m.name AND p.variant_name = v.name
        WHERE {where_clause}
        """

        try:
            df_new = pd.read_sql(sql_new, conn, params=params)
            if min_price is not None and min_price > 0:
                df_new = df_new[df_new["ex_showroom_inr"] >= min_price]
            if max_price is not None and max_price > 0:
                df_new = df_new[df_new["ex_showroom_inr"] <= max_price]
            results.append(df_new)
        except Exception as e:
            print("Error querying new vehicles:", e)

    # 2. Search Used Vehicles
    if vehicle_type in ["All", "Used"]:
        conditions = ["1=1"]
        params = []

        if brand:
            conditions.append("u.make LIKE ?")
            params.append(f"%{brand}%")
        if model:
            conditions.append("u.model LIKE ?")
            params.append(f"%{model}%")
        if fuel_type:
            conditions.append("u.fuel_type LIKE ?")
            params.append(f"%{fuel_type}%")
        if transmission:
            conditions.append("u.transmission LIKE ?")
            params.append(f"%{transmission}%")
        if min_price is not None and min_price > 0:
            conditions.append("u.price_inr >= ?")
            params.append(min_price)
        if max_price is not None and max_price > 0:
            conditions.append("u.price_inr <= ?")
            params.append(max_price)
        if city:
            conditions.append("u.city_name = ?")
            params.append(city)
        if query:
            conditions.append(
                "(u.make LIKE ? OR u.model LIKE ? OR u.variant LIKE ?)"
            )
            q_param = f"%{query}%"
            params.extend([q_param, q_param, q_param])

        where_clause = " AND ".join(conditions)

        sql_used = f"""
        SELECT 
            u.make AS brand,
            u.model AS model,
            u.variant AS variant,
            u.fuel_type AS fuel_type,
            u.transmission AS transmission,
            NULL AS mileage_kmpl,
            NULL AS engine_cc,
            u.price_inr AS ex_showroom_inr,
            u.price_inr AS on_road_inr,
            u.city_name AS city,
            'Used' AS vehicle_type
        FROM used_listings u
        WHERE {where_clause}
        """

        try:
            df_used = pd.read_sql(sql_used, conn, params=params)
            results.append(df_used)
        except Exception as e:
            print("Error querying used vehicles:", e)

    conn.close()

    if results:
        df_combined = pd.concat(results, ignore_index=True)
        # Drop exact duplicates and limit
        df_combined = df_combined.drop_duplicates(
            subset=["brand", "model", "variant", "fuel_type", "transmission"]
        )
        return df_combined.head(limit)
    return pd.DataFrame()


def get_vehicle_details(model_name: str) -> Dict[str, Any]:
    """Retrieve comprehensive specs, variants, and pricing for a single model."""
    conn = get_connection()
    
    # Model & Brand info
    model_df = pd.read_sql("""
    SELECT m.name AS model_name, b.name AS brand_name, m.status, m.launched_at, m.brochure_path
    FROM models m
    JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
    WHERE m.name = ?
    LIMIT 1
    """, conn, params=[model_name])

    # Variants info
    variants_df = pd.read_sql("""
    SELECT 
        v.name AS variant_name,
        v.fuel_type_name AS fuel_type,
        v.transmission_name AS transmission,
        v.engine_cc,
        v.mileage_kmpl,
        v.seats,
        v.key_features,
        p.min_ex_showroom,
        p.max_ex_showroom,
        p.min_on_road,
        p.max_on_road
    FROM variants v
    JOIN models m ON v.model_source_id = m.source_id
    LEFT JOIN (
        SELECT model_name, variant_name,
               MIN(ex_showroom_inr) AS min_ex_showroom,
               MAX(ex_showroom_inr) AS max_ex_showroom,
               MIN(on_road_inr) AS min_on_road,
               MAX(on_road_inr) AS max_on_road
        FROM prices
        GROUP BY model_name, variant_name
    ) p ON p.model_name = m.name AND p.variant_name = v.name
    WHERE m.name = ?
    ORDER BY v.engine_cc ASC, v.name ASC
    """, conn, params=[model_name])

    conn.close()

    if model_df.empty:
        return {}

    return {
        "model": model_df.iloc[0].to_dict(),
        "variants": variants_df
    }


def get_comparison_data(model_names: List[str]) -> pd.DataFrame:
    """Retrieve side-by-side comparison metrics for multiple models."""
    if not model_names:
        return pd.DataFrame()

    conn = get_connection()
    placeholders = ",".join(["?"] * len(model_names))

    query = f"""
    SELECT 
        m.name AS model_name,
        b.name AS brand_name,
        COUNT(DISTINCT v.name) AS total_variants,
        GROUP_CONCAT(DISTINCT v.fuel_type_name) AS fuel_types,
        GROUP_CONCAT(DISTINCT v.transmission_name) AS transmissions,
        MIN(v.mileage_kmpl) AS min_mileage,
        MAX(v.mileage_kmpl) AS max_mileage,
        MIN(v.engine_cc) AS min_engine_cc,
        MAX(v.engine_cc) AS max_engine_cc,
        MIN(p.ex_showroom_inr) AS min_price,
        MAX(p.ex_showroom_inr) AS max_price,
        MAX(v.seats) AS seating_capacity
    FROM models m
    JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
    LEFT JOIN variants v ON v.model_source_id = m.source_id
    LEFT JOIN prices p ON p.model_name = m.name
    WHERE m.name IN ({placeholders})
    GROUP BY m.name, b.name
    """
    df = pd.read_sql(query, conn, params=model_names)
    conn.close()
    return df


def get_analytics_data() -> Dict[str, pd.DataFrame]:
    """Retrieve aggregated data for interactive Plotly charts."""
    conn = get_connection()

    # 1. Brand-wise average price (New cars)
    brand_prices_df = pd.read_sql("""
    SELECT 
        b.name AS brand,
        ROUND(AVG(p.ex_showroom_inr), 0) AS avg_price,
        MIN(p.ex_showroom_inr) AS min_price,
        MAX(p.ex_showroom_inr) AS max_price,
        COUNT(DISTINCT m.name) AS model_count
    FROM models m
    JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
    JOIN prices p ON p.model_name = m.name
    WHERE p.ex_showroom_inr > 0
    GROUP BY b.name
    HAVING model_count >= 2
    ORDER BY avg_price DESC
    LIMIT 20
    """, conn)

    # 2. Fuel Type Breakdown & Mileage
    fuel_stats_df = pd.read_sql("""
    SELECT 
        v.fuel_type_name AS fuel_type,
        COUNT(DISTINCT v.name) AS variant_count,
        ROUND(AVG(v.mileage_kmpl), 2) AS avg_mileage,
        ROUND(AVG(v.engine_cc), 0) AS avg_engine_cc
    FROM variants v
    WHERE v.fuel_type_name IS NOT NULL AND v.fuel_type_name != ''
    GROUP BY v.fuel_type_name
    ORDER BY variant_count DESC
    """, conn)

    # 3. Mileage vs Engine CC scatter data
    scatter_df = pd.read_sql("""
    SELECT DISTINCT
        m.name AS model,
        b.name AS brand,
        v.fuel_type_name AS fuel_type,
        v.engine_cc,
        v.mileage_kmpl
    FROM variants v
    JOIN models m ON v.model_source_id = m.source_id
    JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
    WHERE v.engine_cc IS NOT NULL 
      AND v.mileage_kmpl IS NOT NULL 
      AND v.mileage_kmpl > 5 
      AND v.mileage_kmpl < 70
      AND v.engine_cc > 500
      AND v.engine_cc < 5000
    LIMIT 300
    """, conn)

    # 4. Used cars price vs km & year
    used_stats_df = pd.read_sql("""
    SELECT 
        make,
        model,
        model_year,
        price_inr,
        km,
        fuel_type,
        transmission
    FROM used_listings
    WHERE price_inr > 50000 AND price_inr < 10000000 AND km > 1000 AND km < 250000
    LIMIT 400
    """, conn)

    # 5. Fuel Prices across States (Petrol & Diesel)
    fuel_prices_df = pd.read_sql("""
    SELECT 
        state_name,
        fuel_type,
        ROUND(AVG(price_inr), 2) AS avg_price
    FROM fuel_prices
    WHERE fuel_type IN ('petrol', 'diesel') AND price_inr > 0
    GROUP BY state_name, fuel_type
    ORDER BY state_name ASC
    """, conn)

    conn.close()

    return {
        "brand_prices": brand_prices_df,
        "fuel_stats": fuel_stats_df,
        "scatter": scatter_df,
        "used_stats": used_stats_df,
        "fuel_prices": fuel_prices_df
    }


def get_recommendation_candidates(
    budget: float,
    fuel_preference: str = "Any",
    seats: int = 5,
    transmission: str = "Any",
    usage: str = "Mixed",
    limit: int = 6
) -> pd.DataFrame:
    """Find candidate vehicles matching user preference constraints."""
    conn = get_connection()
    conditions = ["p.ex_showroom_inr > 0"]
    params = []

    # Budget window: up to 1.15x budget (slight stretch allowed)
    max_budget = budget * 1.15
    min_budget = budget * 0.40
    conditions.append("p.ex_showroom_inr BETWEEN ? AND ?")
    params.extend([min_budget, max_budget])

    if fuel_preference != "Any":
        conditions.append("v.fuel_type_name = ?")
        params.append(fuel_preference)

    if transmission != "Any":
        conditions.append("v.transmission_name LIKE ?")
        params.append(f"%{transmission}%")

    if seats and seats > 5:
        conditions.append("(v.seats >= ? OR v.seats IS NULL)")
        params.append(seats)

    where_clause = " AND ".join(conditions)

    query = f"""
    SELECT 
        b.name AS brand,
        m.name AS model,
        v.name AS variant,
        v.fuel_type_name AS fuel_type,
        v.transmission_name AS transmission,
        v.mileage_kmpl,
        v.engine_cc,
        COALESCE(v.seats, 5) AS seats,
        p.ex_showroom_inr,
        p.on_road_inr
    FROM models m
    JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
    JOIN variants v ON v.model_source_id = m.source_id
    JOIN prices p ON p.model_name = m.name AND p.variant_name = v.name
    WHERE {where_clause}
    GROUP BY m.name
    ORDER BY 
        CASE 
            WHEN ? = 'City' THEN v.mileage_kmpl 
            WHEN ? = 'Highway' THEN v.engine_cc
            ELSE (p.ex_showroom_inr)
        END DESC
    LIMIT ?
    """
    params.extend([usage, usage, limit])

    try:
        df = pd.read_sql(query, conn, params=params)
    except Exception as e:
        print("Error fetching recommendation candidates:", e)
        df = pd.DataFrame()

    # Fallback if strict criteria returned fewer than 3 records
    if len(df) < 3:
        fallback_query = """
        SELECT 
            b.name AS brand,
            m.name AS model,
            v.name AS variant,
            v.fuel_type_name AS fuel_type,
            v.transmission_name AS transmission,
            v.mileage_kmpl,
            v.engine_cc,
            COALESCE(v.seats, 5) AS seats,
            p.ex_showroom_inr,
            p.on_road_inr
        FROM models m
        JOIN brands b ON m.brand_slug = b.slug OR m.brand_source_id = b.source_id
        JOIN variants v ON v.model_source_id = m.source_id
        JOIN prices p ON p.model_name = m.name AND p.variant_name = v.name
        WHERE p.ex_showroom_inr <= ?
        GROUP BY m.name
        ORDER BY v.mileage_kmpl DESC
        LIMIT ?
        """
        df = pd.read_sql(fallback_query, conn, params=[max_budget, limit])

    conn.close()
    return df


def execute_safe_query(
    sql_query: str, 
    limit: int = 50
) -> Tuple[List[str], List[Tuple], Optional[str]]:
    """
    Execute read-only SQL queries with safety validation.
    Prevents any DDL/DML mutation queries.
    Returns: (columns, rows, error_message)
    """
    clean_query = sql_query.strip().rstrip(";")
    upper_query = clean_query.upper()

    # Safety checks
    if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
        return [], [], "Access Denied: Only SELECT and WITH queries are permitted."

    for forbidden in FORBIDDEN_SQL_KEYWORDS:
        # Check as distinct tokens
        if f" {forbidden} " in f" {upper_query} " or upper_query.startswith(f"{forbidden} "):
            return [], [], f"Security Violation: '{forbidden}' operation is not allowed."

    # Enforce LIMIT if not present
    if "LIMIT" not in upper_query:
        clean_query += f" LIMIT {limit}"

    try:
        conn = get_connection(read_only=True)
        cursor = conn.cursor()
        cursor.execute(clean_query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()
        return columns, rows, None
    except sqlite3.Error as e:
        return [], [], str(e)


def get_database_schema_info() -> str:
    """Generate concise schema description of key tables for LLM prompt context."""
    return """
TABLE: brands (b)
  - source_id (TEXT): Unique brand ID
  - name (TEXT): Brand name (e.g. Maruti Suzuki, Hyundai, Tata, Mahindra, BMW, Mercedes-Benz, Toyota)
  - slug (TEXT): Brand slug
  - country (TEXT): Origin country

TABLE: models (m)
  - source_id (TEXT): Unique model ID
  - brand_source_id (TEXT): Links to brands.source_id
  - brand_slug (TEXT): Links to brands.slug
  - name (TEXT): Model name (e.g. Creta, Swift, Nexon, Brezza, Altroz, Harrier, Scorpio)
  - slug (TEXT): Model slug
  - launched_at (TEXT): Launch date
  (Note: Do NOT filter on m.status as it contains NULL values)

TABLE: variants (v)
  - source_id (TEXT): Variant ID
  - model_source_id (TEXT): Links to models.source_id
  - name (TEXT): Variant name (e.g. VXI, ZXI Plus, SX, Pure Diesel, STD)
  - fuel_type_name (TEXT): 'Petrol', 'Diesel', 'CNG', 'Electric'
  - transmission_name (TEXT): 'Manual', 'Automatic', 'Automatic (AMT)', 'Automatic (TC)', etc.
  - engine_cc (REAL): Engine displacement in CC (e.g. 1197.0, 1497.0)
  - mileage_kmpl (REAL): Fuel efficiency in km/litre
  - seats (REAL): Number of seats (e.g. 5.0, 7.0)
  - key_features (TEXT): Features list

TABLE: prices (p)
  - model_name (TEXT): Links to models.name
  - variant_name (TEXT): Links to variants.name
  - city_name (TEXT): City (e.g. Delhi, Mumbai, Bangalore, Ahmedabad)
  - ex_showroom_inr (INTEGER): Ex-showroom price in INR (e.g. 800000 = 8 Lakh)
  - on_road_inr (REAL): On-road price in INR
  - emi_inr (REAL): Monthly EMI

TABLE: used_listings (u)
  - make (TEXT): Manufacturer name
  - model (TEXT): Model name
  - variant (TEXT): Variant
  - model_year (INTEGER): Year of manufacture
  - price_inr (INTEGER): Listing price in INR
  - km (INTEGER): Kilometers driven
  - fuel_type (TEXT): Fuel type
  - transmission (TEXT): Transmission
  - city_name (TEXT): City location

TABLE: fuel_prices (fp)
  - state_name (TEXT): Indian state
  - city (TEXT): City name
  - fuel_type (TEXT): 'petrol', 'diesel', 'regular_e20'
  - price_inr (REAL): Fuel rate per litre in INR
"""
