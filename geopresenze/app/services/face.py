import base64, os, cv2, numpy as np

# Load OpenCV's built-in face detector (no TensorFlow needed)
_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_cascade = cv2.CascadeClassifier(_cascade_path)

def _decode_image(image_b64: str):
    try:
        img_bytes = base64.b64decode(image_b64.split(",")[-1])
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None

def _extract_face(img):
    """Detect and crop the largest face from an image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
    if len(faces) == 0:
        return None
    # Use largest face
    x, y, w, h = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
    face = gray[y:y+h, x:x+w]
    return cv2.resize(face, (100, 100))

def _histogram_similarity(face1, face2):
    """Compare two grayscale face images using histogram correlation."""
    hist1 = cv2.calcHist([face1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([face2], [0], None, [256], [0, 256])
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)
    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return score  # 0.0 to 1.0, higher = more similar

def verify_face(image_b64: str, stored_path: str):
    """
    Compare live webcam face against stored reference photo.
    Returns (verified: bool, confidence: float 0-100).
    """
    if not stored_path or not os.path.exists(stored_path):
        print(f"[Face] stored photo not found: {stored_path}")
        return False, 0.0

    # Decode live image
    live_img = _decode_image(image_b64)
    if live_img is None:
        print("[Face] failed to decode live image")
        return False, 0.0

    # Load stored photo
    stored_img = cv2.imread(stored_path)
    if stored_img is None:
        print(f"[Face] failed to read stored photo: {stored_path}")
        return False, 0.0

    # Extract faces
    live_face = _extract_face(live_img)
    stored_face = _extract_face(stored_img)

    if live_face is None:
        print("[Face] no face detected in live image")
        return False, 0.0
    if stored_face is None:
        print("[Face] no face detected in stored photo")
        return False, 0.0

    # Compare using histogram similarity
    score = _histogram_similarity(live_face, stored_face)
    conf = round(score * 100, 1)
    verified = score >= 0.6  # 60% histogram similarity threshold

    print(f"[Face] similarity={score:.3f} conf={conf}% verified={verified}")
    return verified, conf
