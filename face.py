"""
services/face.py
────────────────
Face verification using InsightFace + ONNX Runtime.

NO tensorflow, NO tf-keras — works on Python 3.14 and any future version.

InsightFace uses the ArcFace model (buffalo_sc) which is:
  - More accurate than DeepFace's default
  - ~80 MB download on first use (vs ~500 MB for tensorflow)
  - Runs on CPU via onnxruntime (no GPU needed)
"""

import base64
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np


# ── Model cache: load once, reuse across Streamlit reruns ──────────────────
_face_app = None


def _get_face_app():
    """Lazy-load InsightFace app. Downloads model weights on first call."""
    global _face_app
    if _face_app is None:
        import insightface
        from insightface.app import FaceAnalysis

        # buffalo_sc = small+fast model, good accuracy, ~80 MB
        # det_size=(320,320) is faster for single-face selfies
        _face_app = FaceAnalysis(
            name="buffalo_sc",
            providers=["CPUExecutionProvider"],
        )
        _face_app.prepare(ctx_id=0, det_size=(320, 320))
    return _face_app


def _load_image_from_b64(image_b64: str) -> np.ndarray | None:
    """Decode a base64 JPEG string into a BGR numpy array."""
    try:
        raw = image_b64.split(",")[-1]          # strip data URI prefix if present
        img_bytes = base64.b64decode(raw)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def _load_image_from_path(path: str) -> np.ndarray | None:
    """Load an image from disk into a BGR numpy array."""
    try:
        img = cv2.imread(path)
        return img
    except Exception:
        return None


def _get_embedding(app, img: np.ndarray) -> np.ndarray | None:
    """
    Detect the largest face in the image and return its 512-d embedding.
    Returns None if no face is found.
    """
    faces = app.get(img)
    if not faces:
        return None
    # Pick the largest face by bounding-box area (most prominent face)
    largest = max(faces, key=lambda f: (
        (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    ))
    return largest.normed_embedding   # already L2-normalised


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised embeddings → range [−1, 1]."""
    return float(np.dot(a, b))


def verify_face(
    image_b64: str,
    stored_face_path: str | None,
    threshold: float = 0.35,          # ArcFace buffalo_sc recommended threshold
) -> tuple[bool, float]:
    """
    Compare a live camera frame against a stored student photo.

    Args:
        image_b64:        Base64-encoded JPEG (with or without data URI prefix).
        stored_face_path: Path to the student's registered face photo on disk.
        threshold:        Cosine-similarity threshold for a positive match.
                          0.35 is the recommended value for buffalo_sc ArcFace.

    Returns:
        (is_verified: bool, confidence_percent: float)
        e.g. (True, 87.4)
    """
    if not stored_face_path or not os.path.exists(stored_face_path):
        return False, 0.0

    try:
        app = _get_face_app()
    except Exception as exc:
        print(f"[face.py] Failed to load InsightFace model: {exc}")
        return False, 0.0

    # ── Load images ────────────────────────────────────────────────────────
    live_img   = _load_image_from_b64(image_b64)
    stored_img = _load_image_from_path(stored_face_path)

    if live_img is None:
        print("[face.py] Could not decode live camera image.")
        return False, 0.0
    if stored_img is None:
        print(f"[face.py] Could not load stored image from {stored_face_path}.")
        return False, 0.0

    # ── Extract embeddings ─────────────────────────────────────────────────
    live_emb   = _get_embedding(app, live_img)
    stored_emb = _get_embedding(app, stored_img)

    if live_emb is None:
        print("[face.py] No face detected in live camera frame.")
        return False, 0.0
    if stored_emb is None:
        print(f"[face.py] No face detected in stored photo: {stored_face_path}")
        return False, 0.0

    # ── Compare ────────────────────────────────────────────────────────────
    sim        = cosine_similarity(live_emb, stored_emb)
    # Convert similarity [−1..1] → confidence [0..100]
    confidence = round(max(0.0, sim) * 100.0, 1)
    verified   = sim >= threshold

    return verified, confidence
