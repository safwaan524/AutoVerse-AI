import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_image_url
from styles import inject_styles, format_price, format_mileage, format_cc, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="Compare — AutoVerse AI", layout="wide", page_icon="⚖️")
inject_styles()
sidebar_brand()
st.markdown('<h2 style="color:#00D2FF">⚖️ Vehicle Comparison</h2>', unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    template='plotly_dark',
    paper_bgcolor='#0B0E14',
    plot_bgcolor='#161B22',
    font=dict(color='#F0F6FC', family='system-ui'),
    margin=dict(l=10, r=10, t=40, b=10),
)

df = load_vehicles()
img_map = load_image_map()

# Create label for selection
df['_label'] = df['make'] + ' ' + df['model'] + ' (' + df['variant'].fillna('') + ') — ' + df['price'].apply(format_price)

# ── Vehicle Selection ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Select Vehicles to Compare (2–3)</div>', unsafe_allow_html=True)
all_labels = df['_label'].tolist()
selected_labels = st.multiselect(
    "Pick 2 or 3 vehicles",
    options=all_labels,
    max_selections=3,
    placeholder="Start typing a brand or model name..."
)

if len(selected_labels) < 2:
    st.info("👆 Please select at least 2 vehicles to compare.")
    # Show popular picks
    st.markdown('<div class="section-title">🌟 Popular Comparisons</div>', unsafe_allow_html=True)
    popular = df.dropna(subset=['price']).sort_values('price').groupby('make').first().head(8).reset_index()
    p_cols = st.columns(4)
    for i, (_, pv) in enumerate(popular.iterrows()):
        with p_cols[i % 4]:
            img_url = get_image_url(pv['make'], pv['model'], img_map)
            try:
                st.image(img_url, use_column_width=True)
            except Exception:
                pass
            st.markdown(f'<div style="font-size:0.8rem;color:#F0F6FC">{pv["make"]} {pv["model"]}</div>', unsafe_allow_html=True)
    st.stop()

# Get selected rows
sel_df = df[df['_label'].isin(selected_labels)].drop_duplicates(subset=['vehicle_id'])

# ── Comparison Table ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📋 Side-by-Side Comparison</div>', unsafe_allow_html=True)

ATTRS = [
    ("💰 Ex-Showroom Price", "price", "price"),
    ("🛣️ On-Road Price", "on_road_price", "price"),
    ("⛽ Fuel Type", "fuel_type", "text"),
    ("⚙️ Transmission", "transmission", "text"),
    ("🔧 Engine", "displacement_cc", "cc"),
    ("📏 Mileage", "mileage_kmpl", "mileage"),
    ("💺 Seats", "seating_capacity", "int"),
    ("🚙 Body Type", "body_type", "text"),
]

n = len(sel_df)
header_cols = st.columns([1] + [2] * n)
header_cols[0].markdown('<div style="color:#8B949E;font-size:0.85rem">Attribute</div>', unsafe_allow_html=True)

for i, (_, v) in enumerate(sel_df.iterrows()):
    img_url = get_image_url(v['make'], v['model'], img_map)
    with header_cols[i + 1]:
        try:
            st.image(img_url, use_column_width=True)
        except Exception:
            pass
        st.markdown(f'<div style="font-size:0.9rem;font-weight:700;color:#F0F6FC;text-align:center">{v["make"]} {v["model"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:0.75rem;color:#8B949E;text-align:center">{str(v.get("variant",""))[:30]}</div>', unsafe_allow_html=True)

st.markdown("---")

for label, col, fmt in ATTRS:
    row_cols = st.columns([1] + [2] * n)
    row_cols[0].markdown(f'<div style="color:#8B949E;font-size:0.85rem;padding:8px 0">{label}</div>', unsafe_allow_html=True)

    # Get values to find best
    vals = []
    for _, v in sel_df.iterrows():
        raw = v.get(col)
        if fmt in ("price", "mileage", "int", "cc") and pd.notna(raw):
            try:
                vals.append(float(raw))
            except Exception:
                vals.append(None)
        else:
            vals.append(None)

    for i, (_, v) in enumerate(sel_df.iterrows()):
        raw = v.get(col)
        # Format
        if fmt == "price":
            display = format_price(raw)
        elif fmt == "mileage":
            display = format_mileage(raw)
        elif fmt == "cc":
            display = format_cc(raw)
        elif fmt == "int":
            display = str(int(raw)) if pd.notna(raw) else "N/A"
        else:
            display = str(raw) if pd.notna(raw) else "N/A"

        # Highlight best
        is_best = False
        if vals[i] is not None and any(vals):
            filtered_vals = [x for x in vals if x is not None]
            if filtered_vals:
                if col in ("mileage_kmpl", "seating_capacity"):
                    is_best = vals[i] == max(filtered_vals)
                elif col in ("price", "displacement_cc"):
                    is_best = vals[i] == min(filtered_vals)

        color = "#00D2FF" if is_best else "#F0F6FC"
        prefix = "✓ " if is_best else ""
        row_cols[i + 1].markdown(
            f'<div style="color:{color};font-weight:{"700" if is_best else "400"};text-align:center;padding:8px 0">{prefix}{display}</div>',
            unsafe_allow_html=True
        )

    st.markdown('<hr style="border-color:#1F2937;margin:0">', unsafe_allow_html=True)

# ── Visual Comparison Charts ─────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Visual Comparison</div>', unsafe_allow_html=True)

chart_df = sel_df[['make', 'model', 'price', 'mileage_kmpl', 'displacement_cc']].copy()
chart_df['Label'] = chart_df['make'] + ' ' + chart_df['model']
chart_df['Price (₹L)'] = chart_df['price'] / 100000
chart_df = chart_df.dropna(subset=['price'])

c1, c2, c3 = st.columns(3)

with c1:
    fig = px.bar(chart_df, x='Label', y='Price (₹L)', title='Price (₹ Lakh)',
                 color='Label', template='plotly_dark')
    fig.update_layout(PLOTLY_LAYOUT, showlegend=False, height=300)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    mdf = chart_df.dropna(subset=['mileage_kmpl'])
    if not mdf.empty:
        fig2 = px.bar(mdf, x='Label', y='mileage_kmpl', title='Mileage (km/l)',
                      color='Label', template='plotly_dark')
        fig2.update_layout(PLOTLY_LAYOUT, showlegend=False, height=300)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Mileage data not available for comparison.")

with c3:
    cdf = chart_df.dropna(subset=['displacement_cc'])
    if not cdf.empty:
        fig3 = px.bar(cdf, x='Label', y='displacement_cc', title='Engine (cc)',
                      color='Label', template='plotly_dark')
        fig3.update_layout(PLOTLY_LAYOUT, showlegend=False, height=300)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Engine data not available.")
