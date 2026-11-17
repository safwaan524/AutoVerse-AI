import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_stats, get_image_url
from styles import inject_styles, format_price, format_mileage, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="Home — AutoVerse AI", layout="wide", page_icon="🏠")
inject_styles()
sidebar_brand()

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-container">
  <div style="display:flex;align-items:center;gap:20px">
    <div style="flex:1">
      <div class="hero-title">AutoVerse AI</div>
      <div class="hero-sub">Intelligent Indian Automotive Discovery & Analytics Platform</div>
      <div style="margin-top:12px">
        <span class="hero-pill">🚗 Indian Market Focus</span>&nbsp;
        <span class="hero-pill">🤖 AI-Powered</span>&nbsp;
        <span class="hero-pill">📊 Real-Time Analytics</span>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── STATS ROW ─────────────────────────────────────────────────────────────────
stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">{stats['total_vehicles']:,}</div>
        <div class="stat-label">🚗 Total Variants</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">{stats['total_makes']}</div>
        <div class="stat-label">🏭 Manufacturers</div>
    </div>""", unsafe_allow_html=True)
with col3:
    avg_l = stats['avg_price'] / 100000
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">₹{avg_l:.1f}L</div>
        <div class="stat-label">💰 Avg Ex-Showroom</div>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">{fuel_emoji(stats['top_fuel'])} {stats['top_fuel']}</div>
        <div class="stat-label">⛽ Top Fuel Type</div>
    </div>""", unsafe_allow_html=True)

# ── FEATURED VEHICLES ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">⭐ Featured Vehicles</div>', unsafe_allow_html=True)
df = load_vehicles()
img_map = load_image_map()

# Pick one top-priced vehicle per body type for variety
featured = df.dropna(subset=['price']).sort_values('price', ascending=False)
featured = featured.drop_duplicates(subset=['body_type']).head(6)

cols = st.columns(3)
for i, (_, row) in enumerate(featured.iterrows()):
    with cols[i % 3]:
        img_url = get_image_url(row['make'], row['model'], img_map)
        st.markdown('<div class="vcard">', unsafe_allow_html=True)
        try:
            st.image(img_url, use_column_width=True)
        except Exception:
            st.image(
                "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/"
                "No_image_available_450_x_300.svg/450px-No_image_available_450_x_300.svg.png",
                use_column_width=True
            )
        st.markdown(f"""
        <div class="vcard-title">{row['make']} {row['model']}</div>
        <div class="vcard-price">{format_price(row['price'])}</div>
        <span class="vcard-tag">{fuel_emoji(row['fuel_type'])} {row['fuel_type']}</span>
        <span class="vcard-tag">{body_emoji(row['body_type'])} {row['body_type']}</span>
        </div>""", unsafe_allow_html=True)

# ── TOP BRANDS BY VEHICLE COUNT ───────────────────────────────────────────────
st.markdown('<div class="section-title">🏭 Top Manufacturers</div>', unsafe_allow_html=True)
brand_counts = df.groupby('make').size().sort_values(ascending=False).head(10).reset_index()
brand_counts.columns = ['Brand', 'Variants']
fig = px.bar(
    brand_counts, x='Variants', y='Brand', orientation='h',
    color='Variants', color_continuous_scale='Blues',
    template='plotly_dark'
)
fig.update_layout(
    paper_bgcolor='#0B0E14', plot_bgcolor='#161B22',
    margin=dict(l=0, r=0, t=10, b=10), height=320,
    showlegend=False, coloraxis_showscale=False,
    yaxis=dict(autorange='reversed')
)
fig.update_traces(marker_line_width=0)
st.plotly_chart(fig, use_container_width=True)

# ── QUICK NAVIGATION TILES ────────────────────────────────────────────────────
st.markdown('<div class="section-title">🧭 Explore AutoVerse AI</div>', unsafe_allow_html=True)
n1, n2, n3, n4 = st.columns(4)
with n1:
    st.page_link("pages/2_🔍_Explore.py", label="🔍 Explore Vehicles", use_container_width=True)
with n2:
    st.page_link("pages/4_⚖️_Compare.py", label="⚖️ Compare Cars", use_container_width=True)
with n3:
    st.page_link("pages/5_📊_Analytics.py", label="📊 Price Analytics", use_container_width=True)
with n4:
    st.page_link("pages/6_🤖_AI_Assistant.py", label="🤖 AI Assistant", use_container_width=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**📦 Data Source**")
    st.caption("CardDekho/CarWale via autoverse.db")
    st.markdown(f"**🚗 Total Variants:** {stats['total_vehicles']:,}")
    st.info("🔍 Use Explore to search and filter vehicles")
