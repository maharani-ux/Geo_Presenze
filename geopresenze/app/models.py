from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=True)
    face_path  = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'student_id': self.student_id,
                'name': self.name, 'email': self.email,
                'has_face': self.face_path is not None}

class Session(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    course_name = db.Column(db.String(100))
    room        = db.Column(db.String(50))
    start_time  = db.Column(db.DateTime, nullable=False)
    end_time    = db.Column(db.DateTime, nullable=False)
    lat         = db.Column(db.Float, nullable=False)
    lng         = db.Column(db.Float, nullable=False)
    radius_m    = db.Column(db.Float, default=100.0)

    def to_dict(self):
        return {'id': self.id, 'course_code': self.course_code,
                'course_name': self.course_name, 'room': self.room,
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'lat': self.lat, 'lng': self.lng, 'radius_m': self.radius_m}

class Attendance(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    session_id  = db.Column(db.Integer, db.ForeignKey("session.id"), nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    status      = db.Column(db.String(10))
    distance_m  = db.Column(db.Float)
    face_conf   = db.Column(db.Float)
    flagged     = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(300))
    student     = db.relationship("Student", backref="attendances")
    session_rel = db.relationship("Session", backref="attendances")

    def to_dict(self):
        return {'id': self.id,
                'student_name': self.student.name if self.student else None,
                'student_id':   self.student.student_id if self.student else None,
                'course_code':  self.session_rel.course_code if self.session_rel else None,
                'timestamp':    self.timestamp.isoformat(),
                'status': self.status, 'distance_m': self.distance_m,
                'face_conf': self.face_conf, 'flagged': self.flagged,
                'flag_reason': self.flag_reason}
