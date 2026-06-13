"""
services/face.py
────────────────
Face verification using DeepFace.
DeepFace is imported INSIDE the function (lazy load) so it does NOT
block Streamlit startup or cause import-time weight downloads.
"""
import base64
import os
import tempfile

import cv2
import numpy as np


def verify_face(
    image_b64:        str,
    stored_face_path: str | None,
) -> tuple[bool, float]:
    """
    Compare a live camera frame (base64 JPEG) against a stored student photo.

    Args:
        image_b64:        Base64-encoded JPEG string (with or without data URI prefix).
        stored_face_path: Filesystem path to the student's registered photo.

    Returns:
        (is_verified, confidence_percent)   e.g. (True, 87.3)
    """
    if not stored_face_path or not os.path.exists(stored_face_path):
        return False, 0.0

    # ── Decode base64 → numpy image ────────────────────────────────────────
    try:
        raw = image_b64.split(",")[-1]          # strip "data:image/jpeg;base64," prefix
        img_bytes = base64.b64decode(raw)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False, 0.0
    except Exception:
        return False, 0.0

    # ── Write to temp file (DeepFace needs a file path) ────────────────────
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        cv2.imwrite(tmp.name, img)
        tmp_path = tmp.name

    try:
        from deepface import DeepFace   # ← lazy import: loads weights on first call only

        result = DeepFace.verify(
            img1_path        = tmp_path,
            img2_path        = stored_face_path,
            model_name       = "Facenet512",    # best accuracy
            detector_backend = "retinaface",    # best face detector
            enforce_detection= True,
        )
        verified   = result["verified"]
        distance   = result["distance"]
        confidence = round((1.0 - distance) * 100.0, 1)
        return verified, max(0.0, confidence)

    except Exception as exc:
        print(f"[face.py] DeepFace error: {exc}")
        return False, 0.0

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
