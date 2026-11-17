import streamlit as st
import pandas as pd
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import load_vehicles, load_image_map, get_image_url
from styles import inject_styles, format_price, format_mileage, fuel_emoji, body_emoji, sidebar_brand

st.set_page_config(page_title="AI Assistant — AutoVerse AI", layout="wide", page_icon="🤖")
inject_styles()
sidebar_brand()

st.markdown("""
<div class="hero-container">
  <div class="hero-title" style="font-size:2rem">🤖 AutoVerse AI Assistant</div>
  <div class="hero-sub">Ask me anything about Indian cars — I'll help you find the perfect vehicle</div>
</div>
""", unsafe_allow_html=True)

df = load_vehicles()


def _rule_based(query: str, df: pd.DataFrame) -> str:
    q = query.lower().strip()

    # Budget parsing
    budget_match = re.search(r'(?:under|below|within|budget|less than)\s*[₹rs\.]*\s*(\d+)\s*(lakh|l|lac|cr)?', q)
    if budget_match or any(w in q for w in ['cheap', 'affordable', 'budget', 'economical']):
        budget = 1_000_000  # 10L default
        if budget_match:
            amount = int(budget_match.group(1))
            unit = budget_match.group(2) or ''
            if 'cr' in unit:
                budget = amount * 10_000_000
            elif amount < 100:
                budget = amount * 100_000  # assume lakhs
            else:
                budget = amount
        cars = df[df['price'] <= budget].dropna(subset=['price']).sort_values('price').head(5)
        if cars.empty:
            return f"No cars found under ₹{budget//100000}L in our database. Try a higher budget."
        lines = [f"**Best cars under ₹{budget//100000}L:**\n"]
        for _, c in cars.iterrows():
            ml = f"{c['mileage_kmpl']:.1f} km/l" if pd.notna(c.get('mileage_kmpl')) else "N/A"
            lines.append(f"- **{c['make']} {c['model']}** ({c.get('variant','')[:25]}) — {format_price(c['price'])} | {c.get('fuel_type','N/A')} | {ml} mileage")
        return "\n".join(lines)

    # Mileage / fuel efficiency
    if any(w in q for w in ['mileage', 'fuel efficient', 'efficient', 'economy', 'km/l', 'kmpl']):
        cars = df.dropna(subset=['mileage_kmpl']).sort_values('mileage_kmpl', ascending=False).head(5)
        lines = ["**Most Fuel Efficient Cars:**\n"]
        for _, c in cars.iterrows():
            lines.append(f"- **{c['make']} {c['model']}** — {c['mileage_kmpl']:.1f} km/l | {c.get('fuel_type','N/A')} | {format_price(c['price'])}")
        return "\n".join(lines)

    # Family / 7-seater / SUV
    if any(w in q for w in ['family', '7 seat', 'suv', 'spacious', 'large', 'mpv', 'muv', '6 seat']):
        mask = (df['seating_capacity'].fillna(0).astype(float) >= 6) | (df['body_type'].str.contains('SUV|MUV', case=False, na=False))
        cars = df[mask].dropna(subset=['price']).sort_values('price').head(5)
        lines = ["**Best Family Cars & SUVs:**\n"]
        for _, c in cars.iterrows():
            seats = int(c['seating_capacity']) if pd.notna(c.get('seating_capacity')) else 'N/A'
            lines.append(f"- **{c['make']} {c['model']}** — {seats} seats | {format_price(c['price'])} | {c.get('body_type','N/A')}")
        return "\n".join(lines)

    # Automatic
    if 'automatic' in q or 'auto' in q:
        cars = df[df['transmission'].str.lower().str.contains('automatic|amt|cvt|dct', na=False)].dropna(subset=['price']).sort_values('price').head(5)
        lines = ["**Automatic Transmission Cars:**\n"]
        for _, c in cars.iterrows():
            lines.append(f"- **{c['make']} {c['model']}** — {format_price(c['price'])} | {c.get('fuel_type','N/A')} | {c.get('transmission','N/A')}")
        return "\n".join(lines)

    # Electric
    if any(w in q for w in ['electric', 'ev', 'bev', 'battery']):
        cars = df[df['fuel_type'].str.lower() == 'electric'].dropna(subset=['price']).sort_values('price').head(5)
        if cars.empty:
            return "No electric vehicles found in the current filtered dataset."
        lines = ["**Electric Vehicles in India:**\n"]
        for _, c in cars.iterrows():
            lines.append(f"- **{c['make']} {c['model']}** — {format_price(c['price'])} | {format_mileage(c.get('mileage_kmpl'))}")
        return "\n".join(lines)

    # Specific fuel types
    for fuel in ['petrol', 'diesel', 'cng', 'hybrid']:
        if fuel in q:
            cars = df[df['fuel_type'].str.lower() == fuel].dropna(subset=['price']).sort_values('price').head(5)
            if cars.empty:
                return f"No {fuel} cars found with current filters."
            lines = [f"**Best {fuel.title()} Cars:**\n"]
            for _, c in cars.iterrows():
                ml = f"{c['mileage_kmpl']:.1f} km/l" if pd.notna(c.get('mileage_kmpl')) else "N/A"
                lines.append(f"- **{c['make']} {c['model']}** — {format_price(c['price'])} | {ml}")
            return "\n".join(lines)

    # Luxury / premium
    if any(w in q for w in ['luxury', 'premium', 'expensive', 'best', 'top']):
        cars = df.dropna(subset=['price']).sort_values('price', ascending=False).head(5)
        lines = ["**Premium & Luxury Cars:**\n"]
        for _, c in cars.iterrows():
            lines.append(f"- **{c['make']} {c['model']}** — {format_price(c['price'])} | {c.get('fuel_type','N/A')}")
        return "\n".join(lines)

    # City / compact
    if any(w in q for w in ['city', 'urban', 'compact', 'small', 'hatchback']):
        cars = df[df['body_type'].str.contains('Hatchback', na=False)].dropna(subset=['price']).sort_values('price').head(5)
        lines = ["**Best City & Compact Cars (Hatchbacks):**\n"]
        for _, c in cars.iterrows():
            ml = f"{c['mileage_kmpl']:.1f} km/l" if pd.notna(c.get('mileage_kmpl')) else "N/A"
            lines.append(f"- **{c['make']} {c['model']}** — {format_price(c['price'])} | {ml}")
        return "\n".join(lines)

    # Default response with helpful info
    makes = df['make'].value_counts().head(5).index.tolist()
    cheapest = df.dropna(subset=['price']).sort_values('price').iloc[0]
    best_ml = df.dropna(subset=['mileage_kmpl']).sort_values('mileage_kmpl', ascending=False).iloc[0]
    return f"""Hi! I'm AutoVerse AI, your Indian car expert 🚗

**What I know:**
- 📊 **{len(df):,} variants** from **{df['make'].nunique()} manufacturers**
- 💰 Price range: **{format_price(df['price'].min())} – {format_price(df['price'].max())}**
- ⛽ Fuel types: {', '.join(df['fuel_type'].value_counts().head(4).index.tolist())}
- 🏭 Top brands: {', '.join(makes)}

**Most affordable:** {cheapest['make']} {cheapest['model']} at {format_price(cheapest['price'])}
**Best mileage:** {best_ml['make']} {best_ml['model']} at {best_ml['mileage_kmpl']:.1f} km/l

**Try asking me:**
- "Best cars under ₹10 lakh"
- "Most fuel efficient car"  
- "Best SUV for family"
- "Automatic cars under ₹15 lakh"
- "Electric cars in India"
- "Best diesel sedan"
- "Luxury cars in India"
"""


def get_response(query, df):
    # Try Ollama first
    try:
        import ollama
        cheap5 = df.dropna(subset=['price']).sort_values('price').head(5)
        ctx = '\n'.join([f"- {r['make']} {r['model']}: {format_price(r['price'])}, {r.get('fuel_type')}, {r.get('mileage_kmpl')} km/l" for _, r in cheap5.iterrows()])
        system = f"""You are AutoVerse AI, an expert on Indian cars.
Database: {len(df)} variants from {df['make'].nunique()} brands, prices {format_price(df['price'].min())} to {format_price(df['price'].max())}.
Most affordable cars:\n{ctx}
Answer concisely using only factual data. Format responses in markdown."""
        for model in ['llama3.2', 'llama3', 'llama2']:
            try:
                resp = ollama.chat(model=model, messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': query}
                ])
                return resp['message']['content'], f"🤖 Ollama ({model})"
            except Exception:
                continue
    except Exception:
        pass
    return _rule_based(query, df), "📋 Rule-Based Engine"


# Initialize session state
if 'av_chat' not in st.session_state:
    st.session_state.av_chat = []

left_col, right_col = st.columns([65, 35])

with left_col:
    st.markdown('<div class="section-title">💬 Chat with AutoVerse AI</div>', unsafe_allow_html=True)

    # Quick question buttons
    quick_qs = ["Best cars under ₹10L", "Most fuel efficient", "Best SUV", "Automatic under ₹15L", "Electric cars", "Luxury cars"]
    q_cols = st.columns(3)
    for i, qq in enumerate(quick_qs):
        with q_cols[i % 3]:
            if st.button(qq, key=f"qq_{i}", use_container_width=True):
                st.session_state.av_chat.append({"role": "user", "content": qq})
                with st.spinner("Thinking..."):
                    resp, source = get_response(qq, df)
                st.session_state.av_chat.append({"role": "assistant", "content": resp, "source": source})
                st.rerun()

    st.markdown("---")

    # Chat history display
    for msg in st.session_state.av_chat:
        if msg['role'] == 'user':
            st.markdown(f'<div class="chat-label">You</div><div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            source = msg.get('source', '')
            st.markdown(f'<div class="chat-label">AutoVerse AI &nbsp;<span style="color:#8B949E;font-size:0.68rem">{source}</span></div>', unsafe_allow_html=True)
            st.markdown('<div class="chat-bot">', unsafe_allow_html=True)
            st.markdown(msg["content"])  # render markdown properly
            st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("Ask about Indian cars...")
    if user_input:
        st.session_state.av_chat.append({"role": "user", "content": user_input})
        with st.spinner("🤔 Thinking..."):
            resp, source = get_response(user_input, df)
        st.session_state.av_chat.append({"role": "assistant", "content": resp, "source": source})
        st.rerun()

    # Clear button
    if st.session_state.av_chat:
        if st.button("🗑️ Clear Chat"):
            st.session_state.av_chat = []
            st.rerun()

with right_col:
    st.markdown('<div class="section-title">🎯 Smart Picks</div>', unsafe_allow_html=True)

    with st.expander("⚙️ Set Preferences", expanded=True):
        budget_l = st.slider("Max Budget (₹L)", 3, 300, 20)
        pref_fuel = st.selectbox("Fuel", ["Any"] + sorted(df['fuel_type'].dropna().unique().tolist()))
        pref_trans = st.selectbox("Transmission", ["Any"] + sorted(df['transmission'].dropna().unique().tolist()))

    # Filter for recommendations
    rec_df = df[df['price'] <= budget_l * 100000].dropna(subset=['price'])
    if pref_fuel != "Any":
        rec_df = rec_df[rec_df['fuel_type'] == pref_fuel]
    if pref_trans != "Any":
        rec_df = rec_df[rec_df['transmission'] == pref_trans]

    if rec_df.empty:
        rec_df = df.dropna(subset=['price']).sort_values('price').head(5)
        st.caption("(Showing general picks — relax filters for more options)")

    # Sort by mileage (best value)
    rec_df = rec_df.dropna(subset=['mileage_kmpl']).sort_values('mileage_kmpl', ascending=False).head(5)
    if rec_df.empty:
        rec_df = df.dropna(subset=['price']).sort_values('price').head(5)

    img_map = load_image_map()
    for _, v in rec_df.iterrows():
        img_url = get_image_url(v['make'], v['model'], img_map)
        col_a, col_b = st.columns([1, 2])
        with col_a:
            try:
                st.image(img_url, use_column_width=True)
            except Exception:
                pass
        with col_b:
            st.markdown(f"""
<div style="font-size:0.85rem;font-weight:700;color:#F0F6FC">{v['make']} {v['model']}</div>
<div style="color:#00D2FF;font-size:0.9rem">{format_price(v['price'])}</div>
<div style="font-size:0.72rem;color:#8B949E">{fuel_emoji(v['fuel_type'])} {v['fuel_type']} · {format_mileage(v.get('mileage_kmpl'))}</div>
""", unsafe_allow_html=True)
        st.markdown('<hr style="border-color:#1F2937;margin:6px 0">', unsafe_allow_html=True)
