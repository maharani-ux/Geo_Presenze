"""
pages/1_Scan.py
───────────────
Student-facing attendance page.
Uses st.camera_input() for face capture and an HTML component for GPS.
"""
import base64
import os
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from db.database import get_session, init_db
from db.models import Attendance, SessionModel, Student
from services.face import verify_face
from services.geo import check_location, is_gps_suspicious

# ── Setup ────────────────────────────────────────────────────────────────────
os.makedirs("static/faces", exist_ok=True)
init_db()

st.set_page_config(
    page_title="Scan — Geo-Presenze",
    page_icon="📱",
    layout="centered",
)

st.title("📱 Mark attendance")
st.write("Fill in your details, take a photo, and allow location access.")

# ── GPS HTML component ────────────────────────────────────────────────────────
# Uses postMessage to send lat/lng back to Streamlit via session_state.
# The component runs once; coordinates are stored in st.session_state.
GPS_HTML = """
<!DOCTYPE html>
<html>
<head><style>
  body { margin:0; font-family: -apple-system, sans-serif; }
  #box {
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    background: #E1F5EE;
    color: #085041;
    border: 1px solid #5DCAA5;
  }
  #box.err { background:#FCEBEB; color:#791F1F; border-color:#F09595; }
</style></head>
<body>
  <div id="box">Fetching GPS location…</div>
  <script>
    function send(data) {
      window.parent.postMessage({
        type: "streamlit:setComponentValue",
        value: data
      }, "*");
    }

    if (!navigator.geolocation) {
      document.getElementById("box").textContent =
        "Geolocation is not supported by your browser.";
      document.getElementById("box").className = "err";
      send({ error: "not_supported" });
    } else {
      navigator.geolocation.getCurrentPosition(
        function(pos) {
          var c = pos.coords;
          document.getElementById("box").textContent =
            "📍 Lat: " + c.latitude.toFixed(5) +
            ", Lng: " + c.longitude.toFixed(5) +
            "  (±" + Math.round(c.accuracy) + " m)";
          send({ lat: c.latitude, lng: c.longitude, accuracy: c.accuracy });
        },
        function(err) {
          var msgs = {
            1: "Location permission denied — please allow location access and refresh.",
            2: "Location unavailable — try moving outdoors.",
            3: "GPS timed out — refresh and try again."
          };
          document.getElementById("box").textContent = msgs[err.code] || err.message;
          document.getElementById("box").className = "err";
          send({ error: err.message });
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
      );
    }
  </script>
</body>
</html>
"""

# ── Form ──────────────────────────────────────────────────────────────────────
with st.form("attend_form", clear_on_submit=False):
    st.subheader("1 · Your details")
    col1, col2 = st.columns(2)
    student_id = col1.text_input(
        "Student ID", placeholder="e.g. STD-001", help="Enter your registered student ID"
    )
    session_id = col2.number_input(
        "Session ID",
        min_value=1,
        step=1,
        value=1,
        help="Get this from your lecturer",
    )

    st.subheader("2 · Face scan")
    st.caption("Position your face in the oval and click the camera button.")
    photo = st.camera_input("Take a photo")

    st.subheader("3 · Location")
    st.caption("Allow location access when your browser asks.")

    # Render the GPS component
    gps_data = components.html(GPS_HTML, height=52)

    # Manual fallback (hidden under expander — useful for testing in browser)
    with st.expander("Enter coordinates manually (testing only)"):
        st.warning(
            "This bypasses real GPS — only use for development testing.",
            icon="⚠️",
        )
        m1, m2 = st.columns(2)
        manual_lat = m1.number_input(
            "Latitude",  value=3.07380,   format="%.5f", step=0.00001
        )
        manual_lng = m2.number_input(
            "Longitude", value=101.51830, format="%.5f", step=0.00001
        )
        use_manual = st.checkbox("Use these coordinates instead of GPS")

    st.divider()
    submitted = st.form_submit_button(
        "✅  Mark attendance", use_container_width=True, type="primary"
    )


# ── Processing ────────────────────────────────────────────────────────────────
if submitted:
    # ── Validate inputs ──────────────────────────────────────────────────────
    errors = []
    if not student_id.strip():
        errors.append("Student ID is required.")
    if photo is None:
        errors.append("Please take a face photo.")
    if not use_manual and (gps_data is None or "error" in (gps_data or {})):
        errors.append(
            "GPS location not available. "
            "Allow location access or use the manual coordinates option."
        )

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    # ── Resolve coordinates ──────────────────────────────────────────────────
    if use_manual:
        lat, lng, accuracy = manual_lat, manual_lng, None
    else:
        lat      = gps_data["lat"]
        lng      = gps_data["lng"]
        accuracy = gps_data.get("accuracy")

    # ── Database lookup ──────────────────────────────────────────────────────
    db = get_session()
    try:
        student = db.query(Student).filter_by(
            student_id=student_id.strip().upper()
        ).first()
        session = db.query(SessionModel).filter_by(id=int(session_id)).first()

        if not student:
            st.error(f"Student ID **{student_id}** not found. Check with your admin.")
            st.stop()
        if not session:
            st.error(f"Session **{session_id}** not found. Check with your lecturer.")
            st.stop()

        # ── Geo check ────────────────────────────────────────────────────────
        with st.spinner("Checking location…"):
            dist, in_zone = check_location(
                lat, lng, session.lat, session.lng, session.radius_m
            )
            gps_bad = is_gps_suspicious(accuracy)

        # ── Face verification ─────────────────────────────────────────────────
        with st.spinner("Verifying face — this may take 5–10 seconds…"):
            img_b64 = (
                "data:image/jpeg;base64,"
                + base64.b64encode(photo.getvalue()).decode()
            )
            face_ok, conf = verify_face(img_b64, student.face_path)

        # ── Determine status ──────────────────────────────────────────────────
        flags = []
        if not in_zone:
            flags.append(f"outside zone ({dist:.0f} m from campus)")
        if gps_bad:
            flags.append("suspicious GPS accuracy")
        if not face_ok:
            flags.append("face did not match")
        if conf < 70:
            flags.append(f"low face confidence ({conf:.0f}%)")

        flagged = len(flags) > 0
        now     = datetime.utcnow()
        late    = now > session.start_time
        status  = "absent" if flagged else ("late" if late else "present")

        # ── Save record ───────────────────────────────────────────────────────
        record = Attendance(
            student_id  = student.id,
            session_id  = session.id,
            distance_m  = dist,
            face_conf   = conf,
            status      = status,
            flagged     = flagged,
            flag_reason = "; ".join(flags) if flags else None,
        )
        db.add(record)
        db.commit()

        # ── Show result ───────────────────────────────────────────────────────
        st.divider()

        c1, c2, c3 = st.columns(3)
        c1.metric("Status",     status.upper())
        c2.metric("Distance",   f"{dist:.1f} m")
        c3.metric("Face match", f"{conf:.1f}%")

        if status == "present":
            st.success(
                f"✅ Attendance marked for **{student.name}**  "
                f"({session.course_code})"
            )
        elif status == "late":
            st.warning(
                f"⚠️ Marked **late** for **{student.name}**  "
                f"({session.course_code})"
            )
        else:
            st.error(
                f"❌ Attendance **rejected** for **{student.name}**\n\n"
                + "\n".join(f"- {f}" for f in flags)
            )

    finally:
        db.close()
