from flask import Blueprint, request, jsonify, render_template, current_app
from app.models import db, Student, Session, Attendance
from datetime import datetime
import os, sys, re

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
        "faces_dir": current_app.config.get("FACES_DIR"),
        "db_url": current_app.config.get("SQLALCHEMY_DATABASE_URI"),
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

@admin_bp.route("/api/students/import", methods=["POST"])
def import_students():
    """Bulk import students from a CSV or Excel (.xlsx) file.

    Expected columns: student_id, name, email (email is optional).
    Rows where student_id already exists are skipped.
    Returns {"added": N, "skipped": N, "errors": [...]}
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    try:
        import pandas as pd
        if ext == ".csv":
            df = pd.read_csv(file)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file, engine="openpyxl")
        else:
            return jsonify({"error": "Unsupported file type. Use .csv or .xlsx"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400

    required_cols = {"student_id", "name"}
    df.columns = [c.strip().lower() for c in df.columns]
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        return jsonify({"error": f"Missing required columns: {', '.join(missing)}"}), 400

    added = 0
    skipped = 0
    errors = []

    for i, row in df.iterrows():
        sid = str(row.get("student_id", "")).strip()
        name = str(row.get("name", "")).strip()
        email = str(row.get("email", "")).strip() if "email" in df.columns else None
        if email in ("", "nan", "None"):
            email = None

        if not sid or not name or sid == "nan":
            errors.append(f"Row {i+2}: missing student_id or name")
            continue

        if Student.query.filter_by(student_id=sid).first():
            skipped += 1
            continue

        s = Student(student_id=sid, name=name, email=email)
        db.session.add(s)
        added += 1

    db.session.commit()
    return jsonify({"ok": True, "added": added, "skipped": skipped, "errors": errors})

@admin_bp.route("/api/students/face", methods=["POST"])
def upload_face():
    sid   = request.form.get("student_id")
    photo = request.files.get("photo")
    if not sid or not photo:
        return jsonify({"error": "student_id and photo required"}), 400
    s = Student.query.filter_by(student_id=sid).first()
    if not s: return jsonify({"error": "Student not found"}), 404
    faces_dir = current_app.config["FACES_DIR"]
    os.makedirs(faces_dir, exist_ok=True)
    path = os.path.join(faces_dir, f"{sid}.jpg")
    photo.save(path)
    s.face_path = path; db.session.commit()
    return jsonify({"ok": True, "face_path": path})

@admin_bp.route("/api/students/face-url", methods=["POST"])
def face_from_url():
    """Download a face photo from a URL and save it for a student.

    Accepts JSON: {"student_id": "STD-001", "url": "https://..."}
    Google Drive share URLs are automatically converted to direct download URLs.
    """
    import requests as req

    d = request.json or {}
    sid = d.get("student_id", "").strip()
    url = d.get("url", "").strip()

    if not sid or not url:
        return jsonify({"error": "student_id and url are required"}), 400

    s = Student.query.filter_by(student_id=sid).first()
    if not s:
        return jsonify({"error": "Student not found"}), 404

    # Convert Google Drive share URL to direct download URL
    gdrive_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if gdrive_match:
        file_id = gdrive_match.group(1)
        url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        resp = req.get(url, timeout=15, stream=True)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Failed to download image: {str(e)}"}), 400

    content_type = resp.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        # Some URLs (including Drive confirmation pages) may not declare image content type;
        # we still attempt to save and let Pillow validate.
        pass

    faces_dir = current_app.config["FACES_DIR"]
    os.makedirs(faces_dir, exist_ok=True)
    path = os.path.join(faces_dir, f"{sid}.jpg")

    try:
        from PIL import Image
        import io
        img_bytes = resp.content
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.save(path, "JPEG")
    except Exception as e:
        return jsonify({"error": f"Invalid image data: {str(e)}"}), 400

    s.face_path = path
    db.session.commit()
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
