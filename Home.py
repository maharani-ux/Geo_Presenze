"""
Home.py
───────
Geo-Presenze entry point.
Initialises the database and shows the main navigation page.
"""
import os
import streamlit as st
from db.database import init_db

# ── One-time DB setup ───────────────────────────────────────────────────────
init_db()

# Ensure face storage folder exists
os.makedirs("static/faces", exist_ok=True)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Geo-Presenze",
    page_icon="🌍",
    layout="centered",
)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;padding:2rem 0 1rem">
      <div style="font-size:56px">🌍</div>
      <h1 style="font-size:2rem;font-weight:700;margin:.5rem 0 .25rem">Geo-Presenze</h1>
      <p style="color:#555;font-size:1rem">
        Location + face recognition attendance system
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Navigation cards ────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📱 Students")
    st.write("Mark your attendance with face scan and GPS verification.")
    st.page_link("pages/1_Scan.py", label="Go to scan page", icon="📱")

with col2:
    st.markdown("### 📊 Dashboard")
    st.write("View all attendance records, stats, and flagged entries.")
    st.page_link("pages/2_Dashboard.py", label="Open dashboard", icon="📊")

with col3:
    st.markdown("### ⚙️ Admin")
    st.write("Register students, upload face photos, and create sessions.")
    st.page_link("pages/3_Admin.py", label="Admin panel", icon="⚙️")

st.divider()

st.caption(
    "Built with Streamlit · DeepFace · geopy · SQLAlchemy  |  "
    "Camera and GPS require HTTPS"
)
