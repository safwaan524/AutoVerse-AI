import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db import load_vehicles, get_stats, load_image_map, get_image_url
from styles import inject_styles, sidebar_brand, format_price, fuel_emoji, body_emoji

st.set_page_config(
    page_title="AutoVerse AI | Indian Automotive Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_styles()
sidebar_brand()

# ── HERO BANNER ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-container" style="text-align:center; padding: 48px 24px 36px;">
  <div class="hero-title" style="font-size:3.2rem; margin-bottom: 8px;">🚗 AutoVerse AI</div>
  <div class="hero-sub" style="font-size:1.25rem; max-width: 780px; margin: 0 auto 16px;">
    Intelligent Indian Automotive Discovery, Analytics & AI Platform
  </div>
  <div style="display:flex; justify-content:center; gap:10px; flex-wrap:wrap; margin-bottom: 20px;">
    <span class="hero-pill">🇮🇳 4,000+ Indian Vehicles</span>
    <span class="hero-pill">🏭 80+ Manufacturers</span>
    <span class="hero-pill">📸 Genuine Photos</span>
    <span class="hero-pill">🤖 AI Advisory Engine</span>
    <span class="hero-pill">📊 Interactive Analytics</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── TOP STATS BAR ─────────────────────────────────────────────────────────────
stats = get_stats()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">{stats['total_vehicles']:,}</div>
        <div class="stat-label">🚗 Total Verified Variants</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">{stats['total_makes']}</div>
        <div class="stat-label">🏭 Active Manufacturers</div>
    </div>""", unsafe_allow_html=True)
with c3:
    avg_l = stats['avg_price'] / 100000
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">₹{avg_l:.1f}L</div>
        <div class="stat-label">💰 Average Ex-Showroom</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-value">{fuel_emoji(stats['top_fuel'])} {stats['top_fuel']}</div>
        <div class="stat-label">⛽ Dominant Fuel Segment</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── MODULE ACCESS TILES ───────────────────────────────────────────────────────
st.markdown('<div class="section-title">🧭 Platform Modules & Discovery Tools</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_🏠_Home.py", label="🏠 Home Dashboard", use_container_width=True)
    st.caption("Overview, market highlights, and featured vehicles.")
    
    st.page_link("pages/4_⚖️_Compare.py", label="⚖️ Vehicle Comparison", use_container_width=True)
    st.caption("Side-by-side spec comparisons with difference highlighting.")

with col2:
    st.page_link("pages/2_🔍_Explore.py", label="🔍 Explore & Search Vehicles", use_container_width=True)
    st.caption("Filter by price, brand, fuel, transmission, and body type.")
    
    st.page_link("pages/5_📊_Analytics.py", label="📊 Market & Price Analytics", use_container_width=True)
    st.caption("Interactive charts on price trends, segments, and mileage.")

with col3:
    st.page_link("pages/3_🚘_Details.py", label="🚘 Vehicle Specifications", use_container_width=True)
    st.caption("Deep-dive specification sheets and verified pricing.")
    
    st.page_link("pages/6_🤖_AI_Assistant.py", label="🤖 AI Vehicle Assistant", use_container_width=True)
    st.caption("Natural language car advisory grounded on verified market data.")

st.markdown("<br>", unsafe_allow_html=True)
c_gal, _ = st.columns([1, 2])
with c_gal:
    st.page_link("pages/7_🖼️_Gallery.py", label="🖼️ Vehicle Image Gallery", use_container_width=True)
    st.caption("High-resolution photo gallery of Indian cars by manufacturer.")

st.markdown("<br>", unsafe_allow_html=True)

# ── POPULAR PICKS SHOWCASE ────────────────────────────────────────────────────
st.markdown('<div class="section-title">⭐ Featured Indian Automobiles</div>', unsafe_allow_html=True)
df = load_vehicles()
img_map = load_image_map()

featured = df.dropna(subset=['price']).sort_values('price', ascending=False)
featured = featured.drop_duplicates(subset=['body_type']).head(6)

feat_cols = st.columns(3)
for idx, (_, row) in enumerate(featured.iterrows()):
    with feat_cols[idx % 3]:
        st.markdown('<div class="vcard">', unsafe_allow_html=True)
        img_url = get_image_url(row['make'], row['model'], img_map)
        try:
            st.image(img_url, use_container_width=True)
        except Exception:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/No_image_available_450_x_300.svg/450px-No_image_available_450_x_300.svg.png", use_container_width=True)
        
        st.markdown(f"""
        <div class="vcard-title">{row['make']} {row['model']}</div>
        <div class="vcard-price">{format_price(row['price'])}</div>
        <div>
          <span class="vcard-tag">{fuel_emoji(row['fuel_type'])} {row['fuel_type']}</span>
          <span class="vcard-tag">{body_emoji(row['body_type'])} {row['body_type']}</span>
          <span class="vcard-tag">⚙️ {row['transmission']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Specs", key=f"app_feat_{row['vehicle_id']}", use_container_width=True):
            st.session_state['selected_vehicle_id'] = row['vehicle_id']
            st.switch_page("pages/3_🚘_Details.py")
            
        st.markdown('</div>', unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📌 Quick Navigation")
    st.markdown("""
    - [🏠 Home](pages/1_🏠_Home.py)
    - [🔍 Explore](pages/2_🔍_Explore.py)
    - [🚘 Details](pages/3_🚘_Details.py)
    - [⚖️ Compare](pages/4_⚖️_Compare.py)
    - [📊 Analytics](pages/5_📊_Analytics.py)
    - [🤖 AI Assistant](pages/6_🤖_AI_Assistant.py)
    - [🖼️ Gallery](pages/7_🖼️_Gallery.py)
    """)
    st.markdown("---")
    st.caption("AutoVerse AI · B.Tech Portfolio Project")
