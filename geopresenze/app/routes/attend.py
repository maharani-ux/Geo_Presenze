from flask import Blueprint, request, jsonify
from app.models import db, Student, Session, Attendance
from app.services.geo import check_location, is_gps_suspicious
from app.services.face import verify_face
from datetime import datetime

attend_bp = Blueprint("attend", __name__)

@attend_bp.route("/api/attend", methods=["POST"])
def mark_attendance():
    d = request.json or {}
    student_id = d.get("student_id")
    session_id = d.get("session_id")
    lat, lng   = d.get("lat"), d.get("lng")
    accuracy   = d.get("accuracy")
    image_b64  = d.get("image", "")

    if not all([student_id, session_id, lat, lng]):
        return jsonify({"error": "Missing fields"}), 400

    student = Student.query.filter_by(student_id=student_id).first()
    session = Session.query.get(session_id)
    if not student: return jsonify({"error": f"Student {student_id} not found"}), 404
    if not session: return jsonify({"error": f"Session {session_id} not found"}), 404

    dist, in_zone   = check_location(lat, lng, session.lat, session.lng, session.radius_m)
    gps_bad         = is_gps_suspicious(accuracy)
    face_ok, conf   = verify_face(image_b64, student.face_path)

    flags = []
    if not in_zone: flags.append(f"outside zone ({dist:.0f}m)")
    if gps_bad:     flags.append("suspicious GPS accuracy")
    if not face_ok: flags.append("face mismatch")
    if conf < 50:   flags.append(f"low face confidence ({conf:.0f}%)")

    flagged = len(flags) > 0
    now     = datetime.utcnow()
    late    = now > session.start_time
    status  = "absent" if flagged else ("late" if late else "present")

    rec = Attendance(student_id=student.id, session_id=session.id,
                     distance_m=dist, face_conf=conf, status=status,
                     flagged=flagged, flag_reason="; ".join(flags) or None)
    db.session.add(rec)
    db.session.commit()

    return jsonify({"status": status, "flagged": flagged,
                    "flag_reason": "; ".join(flags) or None,
                    "distance_m": round(dist, 1), "face_conf": round(conf, 1),
                    "in_zone": in_zone})
