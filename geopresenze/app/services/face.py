import base64, os, tempfile, cv2, numpy as np

def verify_face(image_b64: str, stored_path: str):
    if not stored_path or not os.path.exists(stored_path):
        return False, 0.0
    try:
        img_bytes = base64.b64decode(image_b64.split(",")[-1])
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False, 0.0
    except Exception:
        return False, 0.0

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        cv2.imwrite(f.name, img)
        tmp = f.name
    try:
        from deepface import DeepFace
        # Try multiple backends — fall back to next if face not detected
        for backend in ["opencv", "retinaface", "mtcnn"]:
            try:
                r = DeepFace.verify(
                    img1_path=tmp, img2_path=stored_path,
                    model_name="Facenet512",
                    detector_backend=backend,
                    enforce_detection=False  # don't crash if face not clearly detected
                )
                conf = round((1 - r["distance"]) * 100, 1)
                print(f"[Face] backend={backend} verified={r['verified']} conf={conf}")
                return r["verified"], max(0.0, conf)
            except Exception as e:
                print(f"[Face] backend={backend} failed: {e}")
                continue
        return False, 0.0
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
