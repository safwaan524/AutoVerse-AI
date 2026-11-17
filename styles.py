"""
AutoVerse AI — Shared UI Styles & Utilities
Inject once per page via inject_styles().
"""


GLOBAL_CSS = """
<style>
/* ── Reset / Base ─────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }

/* ── Dark scrollbar ───────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0B0E14; }
::-webkit-scrollbar-thumb { background: #00D2FF55; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00D2FF; }

/* ── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0E1117 !important;
    border-right: 1px solid #1F2937;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #00D2FF;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Vehicle card ─────────────────────────────────── */
.vcard {
    background: #161B22;
    border: 1px solid #262D38;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 12px;
    transition: border-color .25s, transform .2s, box-shadow .25s;
}
.vcard:hover {
    border-color: #00D2FF66;
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,210,255,.12);
}
.vcard img { border-radius: 10px; }
.vcard-title { font-weight: 700; font-size: 1rem; color: #F0F6FC; margin: 8px 0 2px; }
.vcard-sub   { font-size: 0.78rem; color: #8B949E; }
.vcard-price { font-size: 1.05rem; font-weight: 700; color: #00D2FF; margin: 6px 0 4px; }
.vcard-tag   {
    display: inline-block;
    background: #1F2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 2px 7px;
    font-size: 0.72rem;
    color: #9CA3AF;
    margin: 2px 2px 2px 0;
}

/* ── Hero ─────────────────────────────────────────── */
.hero-container {
    background: linear-gradient(135deg,#111722 0%,#172133 50%,#0d121a 100%);
    border: 1px solid #1F2937;
    border-radius: 16px;
    padding: 32px 36px;
    margin-bottom: 24px;
}
.hero-title {
    font-size: 2.6rem;
    font-weight: 900;
    background: linear-gradient(90deg,#00D2FF 0%,#3B82F6 60%,#8B5CF6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
    margin-bottom: 8px;
}
.hero-sub { color: #9CA3AF; font-size: 1.1rem; margin-bottom: 4px; }
.hero-pill {
    display: inline-block;
    background: rgba(0,210,255,.12);
    border: 1px solid rgba(0,210,255,.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: #00D2FF;
    margin-top: 10px;
}

/* ── Stat cards ───────────────────────────────────── */
.stat-card {
    background: linear-gradient(135deg,#161B22,#1a2030);
    border: 1px solid #262D38;
    border-radius: 14px;
    padding: 20px 18px;
    text-align: center;
}
.stat-value { font-size: 2rem; font-weight: 800; color: #00D2FF; }
.stat-label { font-size: 0.8rem; color: #8B949E; margin-top: 4px; }

/* ── Section titles ───────────────────────────────── */
.section-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #F0F6FC;
    padding-bottom: 8px;
    border-bottom: 2px solid #00D2FF33;
    margin-bottom: 16px;
}

/* ── Spec badge ───────────────────────────────────── */
.spec-row {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #1F2937;
}
.spec-label { width: 48%; color: #8B949E; font-size: 0.85rem; }
.spec-value { width: 52%; color: #F0F6FC; font-size: 0.9rem; font-weight: 600; }

/* ── Compare table ────────────────────────────────── */
.cmp-header { background:#161B22; border-radius:10px; padding:10px; text-align:center; }
.cmp-attr   { color:#8B949E; font-size:0.82rem; padding:8px 0; }
.cmp-val    { color:#F0F6FC; font-weight:600; font-size:0.9rem; padding:8px 6px; text-align:center; }
.cmp-best   { color:#00D2FF !important; }
.cmp-row    { border-bottom:1px solid #1F2937; }

/* ── Chat bubbles ─────────────────────────────────── */
.chat-user {
    background:#1A3A5C;
    border:1px solid #2563EB44;
    border-radius:14px 14px 2px 14px;
    padding:12px 16px;
    margin:6px 0 6px 15%;
    color:#E2E8F0;
    font-size:0.9rem;
}
.chat-bot {
    background:#161B22;
    border:1px solid #00D2FF33;
    border-radius:14px 14px 14px 2px;
    padding:12px 16px;
    margin:6px 15% 6px 0;
    color:#E2E8F0;
    font-size:0.9rem;
}
.chat-label { font-size:0.72rem; color:#8B949E; margin-bottom:4px; }

/* ── Button overrides ─────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg,#0d2137,#1a3a5c) !important;
    border: 1px solid #2563EB55 !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    border-color: #00D2FF !important;
    color: #00D2FF !important;
}
</style>
"""


def inject_styles():
    """Call at the top of each page."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def format_price(price) -> str:
    try:
        p = float(price)
        if p >= 10_000_000:
            return f"₹{p/10_000_000:.2f} Cr"
        return f"₹{p/100_000:.2f} L"
    except Exception:
        return "N/A"


def format_mileage(val) -> str:
    try:
        return f"{float(val):.1f} km/l"
    except Exception:
        return "N/A"


def format_cc(val) -> str:
    try:
        c = float(val)
        return f"{int(c)} cc ({c/1000:.1f}L)"
    except Exception:
        return "N/A"


def fuel_emoji(ft: str) -> str:
    mapping = {"Petrol": "⛽", "Diesel": "🛢️", "Electric": "⚡", "Cng": "🌿",
               "Hybrid": "🔋", "Lpg": "🟡", "Mild Hybrid": "🔋"}
    return mapping.get(str(ft).strip(), "🚗")


def body_emoji(bt: str) -> str:
    mapping = {"Hatchback": "🚗", "Sedan": "🚘", "SUV": "🚙", "MUV / MPV": "🚐",
               "Van": "🚐", "Coupe": "🏎️", "Convertible": "🏎️", "Pickup Truck": "🛻"}
    for k, v in mapping.items():
        if k.lower() in str(bt).lower():
            return v
    return "🚗"


def sidebar_brand():
    """Render the AutoVerse AI sidebar brand block."""
    import streamlit as st
    st.sidebar.markdown("""
<div style="text-align:center;padding:16px 0 8px">
  <div style="font-size:1.6rem;font-weight:900;
    background:linear-gradient(90deg,#00D2FF,#3B82F6);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
    🚗 AutoVerse AI
  </div>
  <div style="font-size:0.72rem;color:#8B949E;margin-top:4px;">
    Indian Automotive Intelligence
  </div>
</div>
<hr style="border-color:#1F2937;margin:8px 0 16px">
""", unsafe_allow_html=True)
