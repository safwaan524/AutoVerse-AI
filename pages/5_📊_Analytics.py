import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_image_url
from styles import inject_styles, format_price, format_mileage, format_cc, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="Analytics — AutoVerse AI", layout="wide", page_icon="📊")
inject_styles()
sidebar_brand()

st.markdown('<h2 style="color:#00D2FF; margin-bottom: 2px;">📊 Price & Market Analytics</h2>', unsafe_allow_html=True)
st.markdown('<div style="color:#8B949E;margin-bottom:20px">Interactive data-driven insights on pricing, efficiency, segments, and brand dynamics in the Indian automotive market</div>', unsafe_allow_html=True)

df = load_vehicles()

# ── SIDEBAR FILTERS ───────────────────────────────────────────────────────────
st.sidebar.markdown("### 🔧 Filter Analytics Data")

all_fuels = sorted(df['fuel_type'].dropna().unique().tolist())
sel_fuels = st.sidebar.multiselect("⛽ Fuel Type", all_fuels, default=[])

all_makes = sorted(df['make'].dropna().unique().tolist())
sel_makes = st.sidebar.multiselect("🏭 Brand", all_makes, default=[])

all_trans = sorted(df['transmission'].dropna().unique().tolist())
sel_trans = st.sidebar.multiselect("⚙️ Transmission", all_trans, default=[])

all_bodies = sorted(df['body_type'].dropna().unique().tolist())
sel_bodies = st.sidebar.multiselect("🚙 Body Style", all_bodies, default=[])

max_p = int(df['price'].max() // 100000) if not df.empty else 500
price_cap = st.sidebar.slider("💰 Max Price (₹ Lakh)", 5, max(500, max_p), 200, step=5)

# Filter dataframe
adf = df[df['price'] <= price_cap * 100000].copy()
if sel_fuels:
    adf = adf[adf['fuel_type'].isin(sel_fuels)]
if sel_makes:
    adf = adf[adf['make'].isin(sel_makes)]
if sel_trans:
    adf = adf[adf['transmission'].isin(sel_trans)]
if sel_bodies:
    adf = adf[adf['body_type'].isin(sel_bodies)]

# ── OVERVIEW METRICS ──────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="stat-card"><div class="stat-value">{len(adf):,}</div><div class="stat-label">🚗 Filtered Vehicles</div></div>', unsafe_allow_html=True)
with m2:
    avg = adf['price'].mean() / 100000 if len(adf) else 0
    st.markdown(f'<div class="stat-card"><div class="stat-value">₹{avg:.1f}L</div><div class="stat-label">💰 Avg Ex-Showroom</div></div>', unsafe_allow_html=True)
with m3:
    top_fuel = adf['fuel_type'].value_counts().index[0] if len(adf) and not adf['fuel_type'].empty else "N/A"
    st.markdown(f'<div class="stat-card"><div class="stat-value">{fuel_emoji(top_fuel)} {top_fuel}</div><div class="stat-label">⛽ Top Fuel Category</div></div>', unsafe_allow_html=True)
with m4:
    top_body = adf['body_type'].value_counts().index[0] if len(adf) and not adf['body_type'].empty else "N/A"
    st.markdown(f'<div class="stat-card"><div class="stat-value">{body_emoji(top_body)} {top_body}</div><div class="stat-label">🚙 Top Body Type</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if adf.empty:
    st.warning("No vehicle data matches the selected filters. Please expand your filter criteria.")
    st.stop()

# Common Plotly Theme configuration
PLOTLY_THEME = dict(
    paper_bgcolor='#0B0E14',
    plot_bgcolor='#161B22',
    font=dict(color='#F0F6FC', family='sans-serif'),
    margin=dict(l=20, r=20, t=40, b=20),
)

# ── CHART ROW 1 ───────────────────────────────────────────────────────────────
row1a, row1b = st.columns(2)

with row1a:
    # 1. Brand-wise Average Vehicle Price
    brand_avg = adf.dropna(subset=['price']).groupby('make')['price'].mean().sort_values(ascending=False).head(15).reset_index()
    brand_avg.columns = ['Brand', 'Avg Price']
    brand_avg['Avg Price (₹L)'] = brand_avg['Avg Price'] / 100000
    fig1 = px.bar(
        brand_avg, x='Avg Price (₹L)', y='Brand', orientation='h',
        title='Average Vehicle Price by Brand (Top 15)',
        color='Avg Price (₹L)', color_continuous_scale='Blues',
        template='plotly_dark'
    )
    fig1.update_layout(PLOTLY_THEME, height=400, coloraxis_showscale=False, yaxis=dict(autorange='reversed'))
    fig1.update_traces(marker_line_width=0, hovertemplate="<b>%{y}</b><br>Avg Price: ₹%{x:.2f}L<extra></extra>")
    st.plotly_chart(fig1, use_container_width=True)

with row1b:
    # 2. Price Distribution Across Vehicles
    pdata = adf.dropna(subset=['price']).copy()
    pdata['Price (₹L)'] = pdata['price'] / 100000
    fig2 = px.histogram(
        pdata, x='Price (₹L)', nbins=35,
        title='Price Distribution Across Vehicles',
        color_discrete_sequence=['#00D2FF'],
        template='plotly_dark'
    )
    fig2.update_layout(PLOTLY_THEME, height=400)
    fig2.update_traces(marker_line_width=0, hovertemplate="Price Range: ₹%{x:.1f}L<br>Count: %{y}<extra></extra>")
    st.plotly_chart(fig2, use_container_width=True)

# ── CHART ROW 2 ───────────────────────────────────────────────────────────────
row2a, row2b = st.columns(2)

with row2a:
    # 3. Fuel-Type Distribution
    fuel_counts = adf['fuel_type'].value_counts().reset_index()
    fuel_counts.columns = ['Fuel', 'Count']
    FUEL_COLORS = {
        'Petrol': '#FF6B35', 'Diesel': '#3B82F6', 'Electric': '#00FF88',
        'Cng': '#00D2FF', 'Hybrid': '#A855F7', 'Lpg': '#F59E0B', 'Mild Hybrid': '#6366F1'
    }
    colors = [FUEL_COLORS.get(f, '#8B949E') for f in fuel_counts['Fuel']]
    fig3 = go.Figure(go.Pie(
        labels=fuel_counts['Fuel'], values=fuel_counts['Count'],
        hole=0.48, marker_colors=colors,
        textinfo='label+percent',
        hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>"
    ))
    fig3.update_layout(
        title='Fuel Type Distribution',
        paper_bgcolor='#0B0E14', plot_bgcolor='#161B22',
        font=dict(color='#F0F6FC'), margin=dict(l=20, r=20, t=40, b=20),
        height=380, legend=dict(orientation='h', y=-0.15, x=0.1)
    )
    st.plotly_chart(fig3, use_container_width=True)

with row2b:
    # 4. Transmission Distribution
    trans_counts = adf['transmission'].value_counts().reset_index()
    trans_counts.columns = ['Transmission', 'Count']
    TRANS_COLORS = {'Manual': '#3B82F6', 'Automatic': '#00D2FF', 'Amt': '#A855F7', 'Cvt': '#F59E0B', 'Dct': '#00FF88'}
    t_colors = [TRANS_COLORS.get(t, '#64748B') for t in trans_counts['Transmission']]
    fig4 = go.Figure(go.Pie(
        labels=trans_counts['Transmission'], values=trans_counts['Count'],
        hole=0.48, marker_colors=t_colors,
        textinfo='label+percent',
        hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>"
    ))
    fig4.update_layout(
        title='Transmission Distribution',
        paper_bgcolor='#0B0E14', plot_bgcolor='#161B22',
        font=dict(color='#F0F6FC'), margin=dict(l=20, r=20, t=40, b=20),
        height=380, legend=dict(orientation='h', y=-0.15, x=0.2)
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── CHART ROW 3 ───────────────────────────────────────────────────────────────
row3a, row3b = st.columns(2)

with row3a:
    # 5. Vehicle Price versus Mileage
    scatter_df = adf.dropna(subset=['price', 'mileage_kmpl']).copy()
    scatter_df['Price (₹L)'] = scatter_df['price'] / 100000
    fig5 = px.scatter(
        scatter_df, x='mileage_kmpl', y='Price (₹L)',
        color='fuel_type', hover_data=['make', 'model'],
        title='Vehicle Price vs. Mileage (Fuel Efficiency)',
        labels={'mileage_kmpl': 'ARAI Certified Mileage (km/l)', 'Price (₹L)': 'Ex-Showroom Price (₹ Lakh)'},
        template='plotly_dark', opacity=0.75
    )
    fig5.update_layout(PLOTLY_THEME, height=400)
    st.plotly_chart(fig5, use_container_width=True)

with row3b:
    # 6. Average Price by Body Type
    body_price = adf.dropna(subset=['price']).groupby('body_type')['price'].mean().reset_index()
    body_price.columns = ['Body Type', 'Avg Price']
    body_price['Avg Price (₹L)'] = body_price['Avg Price'] / 100000
    body_price = body_price.sort_values('Avg Price (₹L)', ascending=False)
    fig6 = px.bar(
        body_price, x='Body Type', y='Avg Price (₹L)',
        title='Average Price by Body Type (₹ Lakh)',
        color='Avg Price (₹L)', color_continuous_scale='Viridis',
        template='plotly_dark'
    )
    fig6.update_layout(PLOTLY_THEME, height=400, coloraxis_showscale=False)
    fig6.update_traces(marker_line_width=0, hovertemplate="<b>%{x}</b><br>Avg Price: ₹%{y:.2f}L<extra></extra>")
    st.plotly_chart(fig6, use_container_width=True)

# ── CHART ROW 4 ───────────────────────────────────────────────────────────────
row4a, row4b = st.columns(2)

with row4a:
    # 7. Vehicle Count by Manufacturer (Top 15)
    make_counts = adf.groupby('make').size().sort_values(ascending=False).head(15).reset_index()
    make_counts.columns = ['Brand', 'Variants']
    fig7 = px.bar(
        make_counts, x='Variants', y='Brand', orientation='h',
        title='Vehicle Variants by Manufacturer (Top 15)',
        color='Variants', color_continuous_scale='Blues',
        template='plotly_dark'
    )
    fig7.update_layout(PLOTLY_THEME, height=400, coloraxis_showscale=False, yaxis=dict(autorange='reversed'))
    fig7.update_traces(marker_line_width=0, hovertemplate="<b>%{y}</b><br>Variants: %{x:,}<extra></extra>")
    st.plotly_chart(fig7, use_container_width=True)

with row4b:
    # 8. Seating Capacity Distribution
    seat_df = adf.dropna(subset=['seating_capacity']).copy()
    seat_df['Seats'] = seat_df['seating_capacity'].astype(int).astype(str) + " Seater"
    seat_counts = seat_df['Seats'].value_counts().reset_index()
    seat_counts.columns = ['Seating', 'Count']
    fig8 = px.bar(
        seat_counts, x='Seating', y='Count',
        title='Vehicle Count by Seating Capacity',
        color='Count', color_continuous_scale='Teal',
        template='plotly_dark'
    )
    fig8.update_layout(PLOTLY_THEME, height=400, coloraxis_showscale=False)
    fig8.update_traces(marker_line_width=0, hovertemplate="<b>%{x}</b><br>Count: %{y:,}<extra></extra>")
    st.plotly_chart(fig8, use_container_width=True)

# ── RAW DATA EXPANDER ─────────────────────────────────────────────────────────
with st.expander("📋 View Underlying Filtered Dataset Table"):
    display_df = adf[['make', 'model', 'variant', 'fuel_type', 'transmission',
                      'displacement_cc', 'mileage_kmpl', 'seating_capacity', 'body_type', 'price']].copy()
    display_df['price'] = display_df['price'].apply(format_price)
    display_df.columns = ['Brand', 'Model', 'Variant', 'Fuel', 'Transmission',
                          'Engine (cc)', 'Mileage (km/l)', 'Seats', 'Body Style', 'Price']
    st.dataframe(display_df, use_container_width=True, height=320)
