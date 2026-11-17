import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_image_url
from styles import inject_styles, format_price, format_mileage, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="Gallery — AutoVerse AI", layout="wide", page_icon="🖼️")
inject_styles()
sidebar_brand()

st.markdown('<h2 style="color:#00D2FF; margin-bottom: 2px;">🖼️ Vehicle Image Gallery</h2>', unsafe_allow_html=True)
st.markdown('<div style="color:#8B949E;margin-bottom:20px">Authentic visual showcase of Indian automobiles · Sourced from genuine dealership inventory & media archives</div>', unsafe_allow_html=True)

df = load_vehicles()
img_map = load_image_map()

# ── SIDEBAR FILTERS ───────────────────────────────────────────────────────────
st.sidebar.markdown("### 🔍 Filter Gallery")

all_makes = sorted(df['make'].dropna().unique().tolist())
sel_makes = st.sidebar.multiselect("🏭 Filter by Brand", all_makes, default=[], placeholder="All Manufacturers")

all_bodies = sorted(df['body_type'].dropna().unique().tolist())
sel_bodies = st.sidebar.multiselect("🚙 Filter by Body Type", all_bodies, default=[], placeholder="All Body Styles")

all_fuels = sorted(df['fuel_type'].dropna().unique().tolist())
sel_fuels = st.sidebar.multiselect("⛽ Filter by Fuel Type", all_fuels, default=[], placeholder="All Fuels")

# Only show models that have genuine images available or deduped models
gallery_df = df.drop_duplicates(subset=['make', 'model']).copy()
gallery_df['img_url'] = gallery_df.apply(lambda r: get_image_url(r['make'], r['model'], img_map), axis=1)

# Apply filters
if sel_makes:
    gallery_df = gallery_df[gallery_df['make'].isin(sel_makes)]
if sel_bodies:
    gallery_df = gallery_df[gallery_df['body_type'].isin(sel_bodies)]
if sel_fuels:
    gallery_df = gallery_df[gallery_df['fuel_type'].isin(sel_fuels)]

# Prioritize genuine photographs over fallback icons
FALLBACK_SUB = "No_image_available"
gallery_df['has_genuine_img'] = ~gallery_df['img_url'].str.contains(FALLBACK_SUB, na=False)
gallery_df = gallery_df.sort_values(by=['has_genuine_img', 'make', 'model'], ascending=[False, True, True])

total_gallery = len(gallery_df)
genuine_count = int(gallery_df['has_genuine_img'].sum())

st.markdown(f"""
<div style="display:flex; gap:16px; align-items:center; margin-bottom:18px; color:#8B949E; font-size:0.9rem">
  <span>Showing <b style="color:#00D2FF">{total_gallery}</b> vehicle models</span>
  <span>•</span>
  <span><b style="color:#00FF88">{genuine_count}</b> genuine vehicle photos available</span>
</div>
""", unsafe_allow_html=True)

if total_gallery == 0:
    st.info("No vehicles match the selected gallery filters.")
    st.stop()

# Pagination for Gallery
items_per_page = 16
total_pages = max(1, (total_gallery + items_per_page - 1) // items_per_page)
if total_pages > 1:
    page_col1, page_col2 = st.columns([1, 4])
    with page_col1:
        current_page = st.selectbox("Page", range(1, total_pages + 1), index=0)
    start_idx = (current_page - 1) * items_per_page
    paged_items = gallery_df.iloc[start_idx : start_idx + items_per_page]
else:
    paged_items = gallery_df

# ── GRID PRESENTATION (4 columns) ─────────────────────────────────────────────
COLS = 4
rows = [paged_items.iloc[i : i + COLS] for i in range(0, len(paged_items), COLS)]

for row_df in rows:
    cols = st.columns(COLS)
    for idx, (_, car) in enumerate(row_df.iterrows()):
        with cols[idx]:
            with st.container():
                st.markdown('<div class="vcard">', unsafe_allow_html=True)
                try:
                    st.image(car['img_url'], use_container_width=True)
                except Exception:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/No_image_available_450_x_300.svg/450px-No_image_available_450_x_300.svg.png", use_container_width=True)
                
                st.markdown(f"""
                <div class="vcard-title">{car['make']} {car['model']}</div>
                <div class="vcard-price">{format_price(car['price'])}</div>
                <div>
                  <span class="vcard-tag">{fuel_emoji(car['fuel_type'])} {car['fuel_type']}</span>
                  <span class="vcard-tag">{body_emoji(car['body_type'])} {car['body_type']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("View Specs ➔", key=f"gal_btn_{car['vehicle_id']}", use_container_width=True):
                    st.session_state['selected_vehicle_id'] = car['vehicle_id']
                    st.switch_page("pages/3_🚘_Details.py")
                
                st.markdown('</div>', unsafe_allow_html=True)
