import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_image_url, search_vehicles
from styles import inject_styles, format_price, format_mileage, format_cc, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="Explore — AutoVerse AI", layout="wide", page_icon="🔍")
inject_styles()
sidebar_brand()

st.markdown('<h2 style="color:#00D2FF">🔍 Explore Vehicles</h2>', unsafe_allow_html=True)

df = load_vehicles()
img_map = load_image_map()

# ── SIDEBAR FILTERS ──────────────────────────────────────────────────────────
st.sidebar.markdown("### 🔧 Filter Vehicles")

search_q = st.sidebar.text_input("🔎 Search", placeholder="e.g. Swift, Honda, SUV...")

# Brand filter
all_makes = sorted(df['make'].dropna().unique().tolist())
sel_makes = st.sidebar.multiselect("🏭 Brand", all_makes)

# Price range in lakhs
price_min_l = int(df['price'].min() // 100000) if df['price'].notna().any() else 1
price_max_l = int(df['price'].max() // 100000) if df['price'].notna().any() else 500
price_range = st.sidebar.slider("💰 Price (₹ Lakh)", price_min_l, min(price_max_l, 500), (price_min_l, min(100, price_max_l)), step=1)

# Fuel type
all_fuels = sorted(df['fuel_type'].dropna().unique().tolist())
sel_fuels = st.sidebar.multiselect("⛽ Fuel Type", all_fuels)

# Transmission
all_trans = sorted(df['transmission'].dropna().unique().tolist())
sel_trans = st.sidebar.multiselect("⚙️ Transmission", all_trans)

# Body type
all_bodies = sorted(df['body_type'].dropna().unique().tolist())
sel_bodies = st.sidebar.multiselect("🚗 Body Type", all_bodies)

# Sort
sort_opt = st.sidebar.selectbox("📋 Sort By", [
    "Price: Low → High", "Price: High → Low",
    "Mileage: Best First", "Name: A → Z"
])

per_page = st.sidebar.select_slider("Results per page", [12, 24, 48], value=24)

# ── APPLY FILTERS ─────────────────────────────────────────────────────────────
filtered = df.copy()

# Search
if search_q:
    filtered = search_vehicles(filtered, search_q)

# Brand
if sel_makes:
    filtered = filtered[filtered['make'].isin(sel_makes)]

# Price range
filtered = filtered[
    (filtered['price'] >= price_range[0] * 100000) &
    (filtered['price'] <= price_range[1] * 100000)
]

# Fuel
if sel_fuels:
    filtered = filtered[filtered['fuel_type'].isin(sel_fuels)]

# Transmission
if sel_trans:
    filtered = filtered[filtered['transmission'].isin(sel_trans)]

# Body
if sel_bodies:
    filtered = filtered[filtered['body_type'].isin(sel_bodies)]

# Sort
if sort_opt == "Price: Low → High":
    filtered = filtered.sort_values('price')
elif sort_opt == "Price: High → Low":
    filtered = filtered.sort_values('price', ascending=False)
elif sort_opt == "Mileage: Best First":
    filtered = filtered.sort_values('mileage_kmpl', ascending=False)
elif sort_opt == "Name: A → Z":
    filtered = filtered.sort_values(['make', 'model'])

# ── RESULTS HEADER ────────────────────────────────────────────────────────────
total = len(filtered)
st.markdown(f'<div style="color:#8B949E;margin-bottom:16px">Showing <b style="color:#00D2FF">{total:,}</b> vehicles</div>', unsafe_allow_html=True)

if total == 0:
    st.warning("No vehicles match your filters. Try relaxing some filters.")
    if st.button("🔄 Reset All Filters"):
        st.rerun()
    st.stop()

# ── PAGINATION ────────────────────────────────────────────────────────────────
total_pages = max(1, (total + per_page - 1) // per_page)
if total_pages > 1:
    page_num = st.select_slider("Page", list(range(1, total_pages + 1)), value=1)
else:
    page_num = 1

start = (page_num - 1) * per_page
page_df = filtered.iloc[start: start + per_page]

# ── VEHICLE GRID (3 columns) ──────────────────────────────────────────────────
cols_per_row = 3
rows = [page_df.iloc[i:i + cols_per_row] for i in range(0, len(page_df), cols_per_row)]

for row_df in rows:
    cols = st.columns(cols_per_row)
    for col_idx, (_, v) in enumerate(row_df.iterrows()):
        with cols[col_idx]:
            img_url = get_image_url(v['make'], v['model'], img_map)
            with st.container():
                try:
                    st.image(img_url, use_column_width=True)
                except Exception:
                    st.image(
                        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/No_image_available_450_x_300.svg/450px-No_image_available_450_x_300.svg.png",
                        use_column_width=True,
                    )

                st.markdown(f"""
<div class="vcard-title">{v['make']} {v['model']}</div>
<div class="vcard-sub">{v.get('variant', '')[:35]}</div>
<div class="vcard-price">{format_price(v['price'])}</div>
<span class="vcard-tag">{fuel_emoji(v['fuel_type'])} {v['fuel_type']}</span>
<span class="vcard-tag">⚙️ {v['transmission']}</span>
<span class="vcard-tag">{format_mileage(v['mileage_kmpl'])}</span>
""", unsafe_allow_html=True)

                if st.button("View Details →", key=f"vd_{v['vehicle_id']}", use_container_width=True):
                    st.session_state['selected_vehicle_id'] = v['vehicle_id']
                    st.switch_page("pages/3_🚘_Details.py")

            st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)
