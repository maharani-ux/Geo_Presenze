"""
pages/2_Dashboard.py
────────────────────
Admin dashboard: live metrics, full attendance table, CSV export,
and a bar chart of daily attendance rates.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from db.database import get_session, init_db
from db.models import Attendance, SessionModel, Student

init_db()

st.set_page_config(
    page_title="Dashboard — Geo-Presenze",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Attendance dashboard")

col_ref, col_btn = st.columns([6, 1])
with col_btn:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# ── Fetch data ────────────────────────────────────────────────────────────────
db = get_session()
try:
    records  = db.query(Attendance).order_by(Attendance.timestamp.desc()).all()
    students = db.query(Student).count()
    sessions = db.query(SessionModel).count()

    total   = len(records)
    present = sum(1 for r in records if r.status == "present")
    late    = sum(1 for r in records if r.status == "late")
    absent  = sum(1 for r in records if r.status == "absent")
    flagged = sum(1 for r in records if r.flagged)
    rate    = round(present / total * 100, 1) if total > 0 else 0.0

    # ── Metrics row ───────────────────────────────────────────────────────────
    st.subheader("Summary")
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Students",  students)
    m2.metric("Sessions",  sessions)
    m3.metric("Total scans", total)
    m4.metric("Present",   present,  delta=None)
    m5.metric("Late",      late)
    m6.metric("Absent",    absent)
    m7.metric("Rate",      f"{rate}%")

    st.divider()

    if not records:
        st.info("No attendance records yet. Students need to scan first.")
    else:
        # ── Build DataFrame ───────────────────────────────────────────────────
        rows = []
        for r in records:
            rows.append({
                "Student":     r.student.name       if r.student  else "—",
                "Student ID":  r.student.student_id if r.student  else "—",
                "Course":      r.session.course_code if r.session else "—",
                "Time":        r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "—",
                "Status":      r.status or "—",
                "Distance (m)": round(r.distance_m, 1) if r.distance_m is not None else "—",
                "Face %":      round(r.face_conf,   1) if r.face_conf  is not None else "—",
                "Flagged":     "⚠️ Yes" if r.flagged else "—",
                "Reason":      r.flag_reason or "—",
            })
        df = pd.DataFrame(rows)

        # ── Filter bar ────────────────────────────────────────────────────────
        st.subheader("Records")
        fcol1, fcol2, fcol3 = st.columns(3)
        status_filter = fcol1.selectbox(
            "Filter by status", ["All", "present", "late", "absent"]
        )
        flag_filter = fcol2.selectbox(
            "Filter by flag", ["All", "Flagged only", "Clean only"]
        )
        search = fcol3.text_input("Search by name or ID", placeholder="e.g. Ahmad")

        dff = df.copy()
        if status_filter != "All":
            dff = dff[dff["Status"] == status_filter]
        if flag_filter == "Flagged only":
            dff = dff[dff["Flagged"] == "⚠️ Yes"]
        elif flag_filter == "Clean only":
            dff = dff[dff["Flagged"] == "—"]
        if search:
            mask = (
                dff["Student"].str.contains(search, case=False, na=False)
                | dff["Student ID"].str.contains(search, case=False, na=False)
            )
            dff = dff[mask]

        # Colour-code the Status column
        def colour_status(val):
            colours = {
                "present": "background-color:#E1F5EE;color:#085041",
                "late":    "background-color:#FAEEDA;color:#633806",
                "absent":  "background-color:#FCEBEB;color:#791F1F",
            }
            return colours.get(val, "")

        styled = dff.style.applymap(colour_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.caption(f"Showing {len(dff)} of {total} records")

        # ── Export ────────────────────────────────────────────────────────────
        csv = dff.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️  Export to CSV",
            data=csv,
            file_name=f"attendance_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        # ── Daily chart ───────────────────────────────────────────────────────
        st.divider()
        st.subheader("Daily attendance rate")
        df_chart = df.copy()
        df_chart["Date"] = pd.to_datetime(df_chart["Time"]).dt.date
        df_chart["Present"] = df_chart["Status"] == "present"
        daily = (
            df_chart.groupby("Date")["Present"]
            .agg(["sum", "count"])
            .rename(columns={"sum": "Present", "count": "Total"})
        )
        daily["Rate %"] = (daily["Present"] / daily["Total"] * 100).round(1)
        st.bar_chart(daily["Rate %"])

finally:
    db.close()
