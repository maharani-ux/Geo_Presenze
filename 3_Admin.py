"""
pages/3_Admin.py
────────────────
Admin panel:
  Tab 1 — Register a new student + upload face photo
  Tab 2 — Create a class session with geo-fence settings
  Tab 3 — View all students and sessions
  Tab 4 — Geo-fence test tool
"""
import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from db.database import get_session, init_db
from db.models import Attendance, SessionModel, Student
from services.geo import check_location

os.makedirs("static/faces", exist_ok=True)
init_db()

st.set_page_config(
    page_title="Admin — Geo-Presenze",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ Admin panel")

tab1, tab2, tab3, tab4 = st.tabs([
    "👤 Register student",
    "📅 Create session",
    "📋 View all data",
    "🗺️ Geo-fence test",
])


# ── TAB 1: Register student ──────────────────────────────────────────────────
with tab1:
    st.subheader("Register a new student")
    st.write(
        "Fill in the student details and upload a clear, front-facing "
        "photo. The photo is used for face verification during attendance."
    )

    with st.form("student_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        sid   = c1.text_input("Student ID *", placeholder="STD-001")
        name  = c2.text_input("Full name *",  placeholder="Ahmad Nabil")
        email = st.text_input("Email (optional)", placeholder="student@example.com")

        st.markdown("**Face photo** — must be a clear, front-facing JPEG/PNG")
        photo = st.file_uploader(
            "Upload photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed"
        )
        if photo:
            st.image(photo, width=180, caption="Preview")

        submitted = st.form_submit_button("Register student", type="primary")

    if submitted:
        if not sid.strip() or not name.strip():
            st.error("Student ID and full name are required.")
        elif photo is None:
            st.error("Please upload a face photo.")
        else:
            db = get_session()
            try:
                existing = db.query(Student).filter_by(
                    student_id=sid.strip().upper()
                ).first()
                if existing:
                    st.error(f"Student ID **{sid}** is already registered.")
                else:
                    face_path = f"static/faces/{sid.strip().upper()}.jpg"
                    with open(face_path, "wb") as f:
                        f.write(photo.getvalue())

                    student = Student(
                        student_id = sid.strip().upper(),
                        name       = name.strip(),
                        email      = email.strip() or None,
                        face_path  = face_path,
                    )
                    db.add(student)
                    db.commit()
                    st.success(
                        f"✅ **{name}** (ID: {sid.upper()}) registered successfully!"
                    )
                    st.info(f"Face photo saved to `{face_path}`")
            except Exception as exc:
                db.rollback()
                st.error(f"Database error: {exc}")
            finally:
                db.close()

    # ── Update face photo ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Update an existing student's face photo")
    with st.form("update_face_form", clear_on_submit=True):
        upd_sid   = st.text_input("Student ID to update", placeholder="STD-001")
        upd_photo = st.file_uploader("New face photo", type=["jpg","jpeg","png"])
        if upd_photo:
            st.image(upd_photo, width=180)
        upd_submitted = st.form_submit_button("Update photo")

    if upd_submitted:
        if not upd_sid.strip() or upd_photo is None:
            st.error("Provide student ID and a new photo.")
        else:
            db = get_session()
            try:
                s = db.query(Student).filter_by(
                    student_id=upd_sid.strip().upper()
                ).first()
                if not s:
                    st.error(f"Student **{upd_sid}** not found.")
                else:
                    path = f"static/faces/{upd_sid.strip().upper()}.jpg"
                    with open(path, "wb") as f:
                        f.write(upd_photo.getvalue())
                    s.face_path = path
                    db.commit()
                    st.success(f"✅ Face photo updated for **{s.name}**")
            finally:
                db.close()


# ── TAB 2: Create session ─────────────────────────────────────────────────────
with tab2:
    st.subheader("Create a new class session")
    st.write(
        "Set the campus GPS coordinates and radius. Students must be within "
        "that radius when they scan."
    )

    with st.form("session_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        code    = c1.text_input("Course code *", placeholder="CS301")
        cname   = c2.text_input("Course name",   placeholder="Algorithms")

        c3, c4 = st.columns(2)
        room    = c3.text_input("Room", placeholder="B203")
        radius  = c4.number_input(
            "Geo-fence radius (m)",
            min_value=10, max_value=500, value=100, step=10,
            help="Recommended: 80–120 m for indoor classrooms",
        )

        st.markdown("**Date and time**")
        dc1, dc2 = st.columns(2)
        start_date = dc1.date_input("Start date", value=datetime.now().date())
        start_time = dc1.time_input("Start time", value=datetime.now().replace(
            minute=0, second=0, microsecond=0
        ).time())
        end_date = dc2.date_input("End date", value=datetime.now().date())
        end_time = dc2.time_input("End time", value=(
            datetime.now().replace(minute=0, second=0, microsecond=0)
            + timedelta(hours=2)
        ).time())

        st.markdown("**Campus GPS coordinates**")
        st.caption(
            "Right-click on Google Maps and choose 'What's here?' to get the coordinates."
        )
        gc1, gc2 = st.columns(2)
        lat = gc1.number_input(
            "Campus latitude",  value=3.07380,   format="%.5f", step=0.00001
        )
        lng = gc2.number_input(
            "Campus longitude", value=101.51830, format="%.5f", step=0.00001
        )

        create = st.form_submit_button("Create session", type="primary")

    if create:
        if not code.strip():
            st.error("Course code is required.")
        else:
            start_dt = datetime.combine(start_date, start_time)
            end_dt   = datetime.combine(end_date, end_time)
            if end_dt <= start_dt:
                st.error("End time must be after start time.")
            else:
                db = get_session()
                try:
                    sess = SessionModel(
                        course_code = code.strip().upper(),
                        course_name = cname.strip() or None,
                        room        = room.strip() or None,
                        start_time  = start_dt,
                        end_time    = end_dt,
                        lat         = lat,
                        lng         = lng,
                        radius_m    = radius,
                    )
                    db.add(sess)
                    db.commit()
                    st.success(
                        f"✅ Session **{code.upper()}** created  "
                        f"(Session ID: **{sess.id}**)"
                    )
                    st.info(
                        f"Tell students to enter Session ID **{sess.id}** "
                        f"on the scan page."
                    )
                except Exception as exc:
                    db.rollback()
                    st.error(f"Error: {exc}")
                finally:
                    db.close()


# ── TAB 3: View all data ──────────────────────────────────────────────────────
with tab3:
    st.subheader("All students")
    db = get_session()
    try:
        students = db.query(Student).order_by(Student.created_at.desc()).all()
        if students:
            st.dataframe(
                pd.DataFrame([{
                    "Student ID": s.student_id,
                    "Name":       s.name,
                    "Email":      s.email or "—",
                    "Face photo": "✅ Yes" if s.face_path and os.path.exists(s.face_path) else "❌ Missing",
                    "Registered": s.created_at.strftime("%Y-%m-%d") if s.created_at else "—",
                } for s in students]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No students registered yet.")

        st.divider()
        st.subheader("All sessions")
        sessions = db.query(SessionModel).order_by(SessionModel.start_time.desc()).all()
        if sessions:
            now = datetime.utcnow()
            st.dataframe(
                pd.DataFrame([{
                    "ID":          s.id,
                    "Course":      s.course_code,
                    "Name":        s.course_name or "—",
                    "Room":        s.room or "—",
                    "Start":       s.start_time.strftime("%Y-%m-%d %H:%M"),
                    "End":         s.end_time.strftime("%Y-%m-%d %H:%M"),
                    "Radius (m)":  s.radius_m,
                    "Status":      "🟢 Live" if s.start_time <= now <= s.end_time else (
                                   "⏳ Upcoming" if now < s.start_time else "✅ Done"
                                   ),
                } for s in sessions]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No sessions created yet.")
    finally:
        db.close()


# ── TAB 4: Geo-fence test ─────────────────────────────────────────────────────
with tab4:
    st.subheader("Geo-fence distance tester")
    st.write(
        "Enter any GPS coordinates to check whether they fall inside "
        "a session's geo-fence. Useful for testing before going live."
    )

    db = get_session()
    try:
        sessions = db.query(SessionModel).order_by(SessionModel.start_time.desc()).all()
    finally:
        db.close()

    if not sessions:
        st.info("Create a session first, then come back to test the geo-fence.")
    else:
        session_opts = {
            f"[{s.id}] {s.course_code} — {s.course_name or ''}": s
            for s in sessions
        }
        chosen_label = st.selectbox("Select session", list(session_opts.keys()))
        chosen = session_opts[chosen_label]

        st.markdown(
            f"Campus centre: **{chosen.lat:.5f}, {chosen.lng:.5f}**  |  "
            f"Radius: **{chosen.radius_m:.0f} m**"
        )

        tc1, tc2 = st.columns(2)
        test_lat = tc1.number_input(
            "Test latitude",  value=chosen.lat,   format="%.5f", step=0.00001
        )
        test_lng = tc2.number_input(
            "Test longitude", value=chosen.lng,   format="%.5f", step=0.00001
        )

        if st.button("Run test", type="primary"):
            dist, in_zone = check_location(
                test_lat, test_lng, chosen.lat, chosen.lng, chosen.radius_m
            )
            r1, r2, r3 = st.columns(3)
            r1.metric("Distance",  f"{dist:.1f} m")
            r2.metric("Radius",    f"{chosen.radius_m:.0f} m")
            r3.metric("Result",    "✅ Inside" if in_zone else "❌ Outside")
            if in_zone:
                st.success(
                    f"This location is **{dist:.1f} m** from campus — "
                    f"within the {chosen.radius_m:.0f} m zone."
                )
            else:
                st.error(
                    f"This location is **{dist:.1f} m** from campus — "
                    f"outside the {chosen.radius_m:.0f} m zone."
                )
