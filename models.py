"""
db/models.py
────────────
SQLAlchemy ORM models: Student, SessionModel, Attendance.
Pure SQLAlchemy — no Flask dependency.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from db.database import Base


class Student(Base):
    __tablename__ = "students"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(120), unique=True, nullable=True)
    face_path  = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="student")

    def __repr__(self):
        return f"<Student {self.student_id} — {self.name}>"


class SessionModel(Base):
    __tablename__ = "sessions"

    id          = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(20), nullable=False)
    course_name = Column(String(100), nullable=True)
    room        = Column(String(50),  nullable=True)
    start_time  = Column(DateTime, nullable=False)
    end_time    = Column(DateTime, nullable=False)
    lat         = Column(Float, nullable=False)
    lng         = Column(Float, nullable=False)
    radius_m    = Column(Float, default=100.0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="session")

    def __repr__(self):
        return f"<Session {self.course_code} @ {self.start_time}>"


class Attendance(Base):
    __tablename__ = "attendance"

    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"), nullable=False)
    session_id  = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    status      = Column(String(10))   # 'present' | 'late' | 'absent'
    distance_m  = Column(Float,   nullable=True)
    face_conf   = Column(Float,   nullable=True)
    flagged     = Column(Boolean, default=False)
    flag_reason = Column(String(300), nullable=True)

    student = relationship("Student",      back_populates="attendances")
    session = relationship("SessionModel", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance student={self.student_id} status={self.status}>"
