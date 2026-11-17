import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_image_url, search_vehicles
from styles import inject_styles, format_price, format_mileage, format_cc, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="Vehicle Details — AutoVerse AI", layout="wide", page_icon="🚘")
inject_styles()
sidebar_brand()

st.markdown('<h2 style="color:#00D2FF">🚘 Vehicle Details</h2>', unsafe_allow_html=True)

df = load_vehicles()
img_map = load_image_map()

vehicle_id = st.session_state.get('selected_vehicle_id')

# ── VEHICLE SELECTION FALLBACK ────────────────────────────────────────────────
if not vehicle_id:
    st.info("No vehicle selected. Search and select below or go to Explore.")
    search_q = st.text_input("Search for a vehicle", placeholder="e.g. Swift, Nexon, Creta...")
    if search_q:
        results = search_vehicles(df, search_q).head(20)
        if results.empty:
            st.warning("No results found.")
        else:
            for _, v in results.iterrows():
                if st.button(
                    f"{v['make']} {v['model']} {v.get('variant', '')} — {format_price(v['price'])}",
                    key=f"sel_{v['vehicle_id']}",
                ):
                    st.session_state['selected_vehicle_id'] = v['vehicle_id']
                    st.rerun()
    st.stop()

# ── FIND AND DISPLAY VEHICLE ──────────────────────────────────────────────────
match = df[df['vehicle_id'] == vehicle_id]
if match.empty:
    st.error("Vehicle not found.")
    st.stop()

v = match.iloc[0]

# Back button
if st.button("← Back to Explore"):
    st.switch_page("pages/2_🔍_Explore.py")

# Two columns: image left, specs right
left, right = st.columns([2, 3])

# ── LEFT COLUMN: Image + name ─────────────────────────────────────────────────
with left:
    img_url = get_image_url(v['make'], v['model'], img_map)
    try:
        st.image(img_url, use_column_width=True)
    except Exception:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/No_image_available_450_x_300.svg/450px-No_image_available_450_x_300.svg.png",
            use_column_width=True,
        )

    st.markdown(f"""
<div style="margin-top:12px">
  <div style="font-size:1.5rem;font-weight:800;color:#F0F6FC">{v['make']} {v['model']}</div>
  <div style="color:#8B949E;margin:4px 0">{v.get('variant', 'N/A')}</div>
  <div style="font-size:1.8rem;font-weight:900;color:#00D2FF;margin-top:8px">{format_price(v['price'])}</div>
  <div style="color:#8B949E;font-size:0.8rem">Ex-Showroom Price</div>
</div>
""", unsafe_allow_html=True)

    # Tags
    tags = []
    if pd.notna(v.get('fuel_type')):
        tags.append(f"{fuel_emoji(v['fuel_type'])} {v['fuel_type']}")
    if pd.notna(v.get('transmission')):
        tags.append(f"⚙️ {v['transmission']}")
    if pd.notna(v.get('body_type')):
        tags.append(f"{body_emoji(v['body_type'])} {v['body_type']}")
    tag_html = " ".join([f'<span class="vcard-tag">{t}</span>' for t in tags])
    st.markdown(f"<div style='margin-top:12px'>{tag_html}</div>", unsafe_allow_html=True)

# ── RIGHT COLUMN: Specs ───────────────────────────────────────────────────────
with right:
    st.markdown('<div class="section-title">📋 Specifications</div>', unsafe_allow_html=True)

    specs = [
        ("🏭 Manufacturer", v.get('make', 'N/A')),
        ("🚗 Model", v.get('model', 'N/A')),
        ("🔖 Variant", v.get('variant', 'N/A')),
        ("💰 Ex-Showroom Price", format_price(v.get('price'))),
        ("🛣️ On-Road Price", format_price(v.get('on_road_price')) if pd.notna(v.get('on_road_price')) else "N/A"),
        ("⛽ Fuel Type", f"{fuel_emoji(v.get('fuel_type', ''))} {v.get('fuel_type', 'N/A')}"),
        ("⚙️ Transmission", v.get('transmission', 'N/A')),
        ("🔧 Engine Capacity", format_cc(v.get('displacement_cc'))),
        ("📏 Mileage (ARAI)", format_mileage(v.get('mileage_kmpl'))),
        ("💺 Seating Capacity", f"{int(v['seating_capacity'])} persons" if pd.notna(v.get('seating_capacity')) else "N/A"),
        ("🚙 Body Type", f"{body_emoji(v.get('body_type', ''))} {v.get('body_type', 'N/A')}"),
    ]

    spec_rows = ""
    for label, value in specs:
        spec_rows += f"""
<div class="spec-row">
  <div class="spec-label">{label}</div>
  <div class="spec-value">{value}</div>
</div>"""

    st.markdown(
        f'<div style="background:#161B22;border-radius:12px;padding:16px;border:1px solid #262D38">{spec_rows}</div>',
        unsafe_allow_html=True,
    )

# ── SIMILAR VEHICLES ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">🔄 Similar Vehicles</div>', unsafe_allow_html=True)

# Find similar: same body_type or fuel_type, similar price range
similar = df[
    (df['vehicle_id'] != vehicle_id) &
    (
        (df['body_type'] == v.get('body_type')) |
        (df['fuel_type'] == v.get('fuel_type'))
    )
].copy()

if pd.notna(v.get('price')):
    p = v['price']
    similar = similar[(similar['price'] >= p * 0.7) & (similar['price'] <= p * 1.4)]

similar = similar.dropna(subset=['price']).head(4)

if not similar.empty:
    sim_cols = st.columns(min(4, len(similar)))
    for i, (_, sv) in enumerate(similar.iterrows()):
        with sim_cols[i]:
            sim_img = get_image_url(sv['make'], sv['model'], img_map)
            try:
                st.image(sim_img, use_column_width=True)
            except Exception:
                pass
            st.markdown(f"""
<div style="font-size:0.85rem;font-weight:700;color:#F0F6FC">{sv['make']} {sv['model']}</div>
<div style="color:#00D2FF;font-size:0.9rem">{format_price(sv['price'])}</div>
<div style="font-size:0.75rem;color:#8B949E">{sv.get('fuel_type', 'N/A')} · {format_mileage(sv.get('mileage_kmpl'))}</div>
""", unsafe_allow_html=True)
            if st.button("View", key=f"sim_{sv['vehicle_id']}", use_container_width=True):
                st.session_state['selected_vehicle_id'] = sv['vehicle_id']
                st.rerun()
