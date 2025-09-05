"""
Auto-capture color face images for a student and retrain LBPH model.

Usage (from terminal):
    python face_recognition/register_user.py <student_id> [<student_name>]

If no arguments are provided it will prompt for student_id (interactive).
"""

import sys
import os
import time
import cv2
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINED_FACES_DIR = os.path.join(BASE_DIR, "trained_faces")
MODEL_PATH = os.path.join(TRAINED_FACES_DIR, "face_model.yml")
os.makedirs(TRAINED_FACES_DIR, exist_ok=True)

# Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def train_model():
    """Train an LBPH recognizer from images under TRAINED_FACES_DIR/<student_id>/*.jpg"""
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except Exception as e:
        print("[ERROR] cv2.face.LBPHFaceRecognizer_create() not available. Install opencv-contrib-python.")
        return False

    faces = []
    ids = []

    for folder_name in os.listdir(TRAINED_FACES_DIR):
        folder_path = os.path.join(TRAINED_FACES_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        # folder name should represent the student id (string or numeric)
        for filename in os.listdir(folder_path):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            img_path = os.path.join(folder_path, filename)
            try:
                pil_img = Image.open(img_path).convert("L")  # convert to grayscale
                img_np = np.array(pil_img, dtype="uint8")
                # histogram equalization to improve quality
                img_np = cv2.equalizeHist(img_np)
                faces.append(img_np)
                # we store folder_name as id; try int if possible else store as text label
                try:
                    ids.append(int(folder_name))
                except:
                    # LBPH requires integer labels; if your student IDs are non-numeric,
                    # you will need a mapping layer. For now, if folder_name is not numeric,
                    # skip it (or change your student_id to numeric).
                    print(f"[WARN] Skipping non-numeric label folder: {folder_name}")
            except Exception as e:
                print(f"[WARN] Could not read {img_path}: {e}")

    if len(faces) == 0:
        print("[WARN] No training images found. Model not saved.")
        # remove stale model to avoid stale recognition
        try:
            if os.path.exists(MODEL_PATH):
                os.remove(MODEL_PATH)
                print("[INFO] Removed stale model file.")
        except:
            pass
        return False

    recognizer.train(faces, np.array(ids))
    recognizer.save(MODEL_PATH)
    print(f"[INFO] Model trained and saved to {MODEL_PATH} ({len(faces)} images).")
    return True

def capture_faces(student_id, samples=5, interval=1.0, timeout=25):
    """
    Auto-capture samples color face images for student_id.
    interval: minimum seconds between saved images.
    timeout: abort after this many seconds.
    """
    save_path = os.path.join(TRAINED_FACES_DIR, str(student_id))
    os.makedirs(save_path, exist_ok=True)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera. Make sure webcam is available.")
        return False

    print(f"[INFO] Starting auto-capture for student {student_id} -> {save_path}")
    count = 0
    start_time = time.time()
    last_saved = 0.0

    # warm-up
    for _ in range(10):
        cap.read()
        time.sleep(0.02)

    while count < samples and (time.time() - start_time) < timeout:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80,80))

        # when face(s) detected and enough time passed since last save
        if len(faces) > 0 and (time.time() - last_saved) >= interval:
            # choose largest face
            faces_sorted = sorted(faces, key=lambda r: r[2]*r[3], reverse=True)
            (x, y, w, h) = faces_sorted[0]
            face_color = frame[y:y+h, x:x+w]
            if face_color.size == 0:
                continue
            face_resized = cv2.resize(face_color, (200, 200))
            file_path = os.path.join(save_path, f"{count+1}.jpg")
            cv2.imwrite(file_path, face_resized)
            count += 1
            last_saved = time.time()
            print(f"[INFO] Saved {file_path} ({count}/{samples})")

            # draw rectangle for feedback
            cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)

        # show live feed so user can position face (optional)
        cv2.imshow(f"Capturing faces for {student_id}", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] Capture aborted by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"[INFO] Capture finished: {count}/{samples} images saved.")

    if count == 0:
        print("[WARN] No images captured; aborting model training.")
        return False

    # retrain model
    return train_model()

if __name__ == "_main_":
    # Accept command-line args or fallback to interactive prompt
    sid = None
    name = None
    if len(sys.argv) >= 2:
        sid = sys.argv[1]
    if len(sys.argv) >= 3:
        name = sys.argv[2]

    if not sid:
        try:
            sid = input("Enter numeric Student ID: ").strip()
        except EOFError:
            print("[ERROR] No Student ID provided and input not available.")
            sys.exit(1)

    # optional validation: ensure numeric label for LBPH
    if not sid.isdigit():
        print("[ERROR] Student ID must be numeric for the recognizer to work (LBPH uses integer labels).")
        print("Either use numeric student IDs or modify recognizer to map text IDs to integers.")
        sys.exit(1)

    ok = capture_faces(sid, samples=5, interval=1.0, timeout=25)
    if ok:
        print("[INFO] Register & training completed.")
        sys.exit(0)
    else:
        print("[ERROR] Register or training failed.")
        sys.exit(2)
