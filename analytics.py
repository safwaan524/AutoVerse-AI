import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, Tuple
from database import get_analytics_data, get_database_stats


def create_brand_price_chart(df: pd.DataFrame) -> go.Figure:
    """Create interactive bar chart of average ex-showroom prices by brand."""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values(by="avg_price", ascending=True)

    fig = px.bar(
        df_sorted,
        x="avg_price",
        y="brand",
        orientation="h",
        title="<b>Brand-wise Average Ex-Showroom Price (INR)</b>",
        labels={"avg_price": "Average Ex-Showroom Price (₹)", "brand": "Automotive Brand"},
        color="avg_price",
        color_continuous_scale="Tealgrn",
        hover_data=["min_price", "max_price", "model_count"]
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161B22",
        plot_bgcolor="#0E1117",
        font=dict(color="#F0F6FC", family="Inter, sans-serif"),
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        coloraxis_showscale=False
    )
    fig.update_traces(
        marker_line_color="#00D2FF",
        marker_line_width=1,
        hovertemplate="<b>%{y}</b><br>Avg Price: ₹%{x:,.0f}<extra></extra>"
    )
    return fig


def create_price_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create histogram of price distribution."""
    if df.empty:
        return go.Figure()

    fig = px.histogram(
        df,
        x="ex_showroom_inr",
        nbins=40,
        title="<b>Market Price Distribution (Ex-Showroom)</b>",
        labels={"ex_showroom_inr": "Price (₹)", "count": "Number of Variants"},
        color_discrete_sequence=["#00D2FF"]
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161B22",
        plot_bgcolor="#0E1117",
        font=dict(color="#F0F6FC", family="Inter, sans-serif"),
        height=380,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig


def create_mileage_vs_engine_chart(df: pd.DataFrame) -> go.Figure:
    """Create scatter plot comparing engine displacement (cc) against mileage (kmpl)."""
    if df.empty:
        return go.Figure()

    fig = px.scatter(
        df,
        x="engine_cc",
        y="mileage_kmpl",
        color="fuel_type",
        hover_name="model",
        hover_data=["brand", "fuel_type"],
        title="<b>Fuel Efficiency (km/l) vs. Engine Displacement (cc)</b>",
        labels={"engine_cc": "Engine Displacement (cc)", "mileage_kmpl": "Mileage (kmpl)", "fuel_type": "Fuel Type"},
        color_discrete_map={
            "Petrol": "#00D2FF",
            "Diesel": "#FFA800",
            "CNG": "#00E676",
            "Electric": "#E040FB"
        }
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161B22",
        plot_bgcolor="#0E1117",
        font=dict(color="#F0F6FC", family="Inter, sans-serif"),
        height=450,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color="#30363D")))
    return fig


def create_fuel_price_chart(df: pd.DataFrame) -> go.Figure:
    """Create grouped bar chart of petrol and diesel prices across Indian states."""
    if df.empty:
        return go.Figure()

    # Filter top 15 states
    top_states = df["state_name"].drop_duplicates().head(16)
    filtered = df[df["state_name"].isin(top_states)]

    fig = px.bar(
        filtered,
        x="state_name",
        y="avg_price",
        color="fuel_type",
        barmode="group",
        title="<b>Regional Fuel Prices Across States (₹ / Litre)</b>",
        labels={"state_name": "State", "avg_price": "Price per Litre (₹)", "fuel_type": "Fuel"},
        color_discrete_map={"petrol": "#00D2FF", "diesel": "#FFA800"}
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161B22",
        plot_bgcolor="#0E1117",
        font=dict(color="#F0F6FC", family="Inter, sans-serif"),
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_tickangle=-45
    )
    return fig


def create_used_car_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Create scatter plot showing depreciation: Used car price vs KM driven."""
    if df.empty:
        return go.Figure()

    fig = px.scatter(
        df,
        x="km",
        y="price_inr",
        color="fuel_type",
        hover_name="model",
        hover_data=["make", "model_year", "transmission"],
        title="<b>Used Car Market: Listing Price vs. Kilometers Driven</b>",
        labels={"km": "Odometer (km)", "price_inr": "Price (₹)", "fuel_type": "Fuel Type"},
        color_discrete_sequence=px.colors.qualitative.Plotly
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#161B22",
        plot_bgcolor="#0E1117",
        font=dict(color="#F0F6FC", family="Inter, sans-serif"),
        height=420,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig
