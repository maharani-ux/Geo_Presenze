from flask import Blueprint, request, jsonify, render_template, current_app
from app.models import db, Student, Session, Attendance
from datetime import datetime
import os, sys

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/api/debug")
def debug():
    import platform
    students = Student.query.all()
    try:
        import psutil
        mem = psutil.virtual_memory()
        mem_info = {"total_mb": mem.total//1024//1024, "available_mb": mem.available//1024//1024, "percent": mem.percent}
    except Exception:
        mem_info = "psutil not available"
    return jsonify({
        "python": sys.version,
        "platform": platform.platform(),
        "memory": mem_info,
        "students": [{"id": s.student_id, "name": s.name, "face_path": s.face_path,
                      "face_exists": os.path.exists(s.face_path) if s.face_path else False}
                     for s in students],
        "static_folder": current_app.static_folder,
    })

@admin_bp.route("/")
def dashboard(): return render_template("dashboard.html")

@admin_bp.route("/scan")
def scan_page(): return render_template("scan.html")

@admin_bp.route("/api/students", methods=["GET"])
def list_students():
    return jsonify([s.to_dict() for s in Student.query.all()])

@admin_bp.route("/api/students", methods=["POST"])
def add_student():
    d = request.json
    if Student.query.filter_by(student_id=d["student_id"]).first():
        return jsonify({"error": "Student ID already exists"}), 409
    s = Student(student_id=d["student_id"], name=d["name"], email=d.get("email"))
    db.session.add(s); db.session.commit()
    return jsonify({"ok": True, "id": s.id})

@admin_bp.route("/api/students/face", methods=["POST"])
def upload_face():
    sid   = request.form.get("student_id")
    photo = request.files.get("photo")
    if not sid or not photo:
        return jsonify({"error": "student_id and photo required"}), 400
    s = Student.query.filter_by(student_id=sid).first()
    if not s: return jsonify({"error": "Student not found"}), 404
    faces_dir = os.path.join(current_app.static_folder, "faces")
    os.makedirs(faces_dir, exist_ok=True)
    path = os.path.join(faces_dir, f"{sid}.jpg")
    photo.save(path)
    s.face_path = path; db.session.commit()
    return jsonify({"ok": True, "face_path": path})

@admin_bp.route("/api/sessions", methods=["GET"])
def list_sessions():
    return jsonify([s.to_dict() for s in Session.query.order_by(Session.start_time.desc()).all()])

@admin_bp.route("/api/sessions", methods=["POST"])
def add_session():
    d = request.json
    sess = Session(
        course_code=d["course_code"], course_name=d.get("course_name", ""),
        room=d.get("room", ""),
        start_time=datetime.fromisoformat(d["start_time"]),
        end_time=datetime.fromisoformat(d["end_time"]),
        lat=d["lat"], lng=d["lng"], radius_m=d.get("radius_m", 100)
    )
    db.session.add(sess); db.session.commit()
    return jsonify({"ok": True, "id": sess.id})

@admin_bp.route("/api/attendance")
def get_attendance():
    return jsonify([r.to_dict() for r in Attendance.query.order_by(Attendance.timestamp.desc()).all()])

@admin_bp.route("/api/stats")
def get_stats():
    total   = Attendance.query.count()
    present = Attendance.query.filter_by(status="present").count()
    late    = Attendance.query.filter_by(status="late").count()
    return jsonify({
        "total": total, "present": present, "late": late,
        "absent": total - present - late,
        "flagged": Attendance.query.filter_by(flagged=True).count(),
        "students": Student.query.count(),
        "sessions": Session.query.count(),
        "rate": round(present / total * 100, 1) if total > 0 else 0
    })
