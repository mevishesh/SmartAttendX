#!/usr/bin/env python3
import cv2
import numpy as np
import os, sqlite3
from datetime import datetime
import pyttsx3
import sounddevice as sd
import soundfile as sf
import librosa
from scipy.spatial.distance import cosine
import time

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "../database/database.db")
TRAINED_DIR = os.path.join(BASE_DIR, "trained_faces")
MODEL_PATH = os.path.join(TRAINED_DIR, "face_model.yml")


# ---------- Step 1: Mark All Absent ----------
def mark_all_absent():
    """Mark all students as Absent for today (only if not already marked)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # Check if attendance already initialized today
    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
    count = c.fetchone()[0]

    if count > 0:
        print(f"[INFO] Attendance already initialized for {today}. Skipping Absent marking.")
        conn.close()
        return

    # Fetch all students with their admin_id
    c.execute("SELECT id, admin_id FROM students")
    students = c.fetchall()

    for student_id, admin_id in students:
        c.execute("""
            INSERT OR IGNORE INTO attendance (student_id, date, status, admin_id)
            VALUES (?, ?, ?, ?)
        """, (student_id, today, "Absent", admin_id))

    conn.commit()
    conn.close()
    print("[INFO] All students marked as Absent for today.")


# ---------- Step 2: Load Face Recognition Model ----------
recognizer = None
if os.path.exists(MODEL_PATH):
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_PATH)
        print("[INFO] Face model loaded.")
    except Exception as e:
        print("[WARN] Could not load recognizer model:", e)

# ---------- Step 3: Load Haar Cascade ----------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ---------- Step 4: Text-to-Speech ----------
engine = pyttsx3.init()


# ---------- Step 5: Get Student Map ----------
def get_student_map():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    students = c.execute("SELECT student_id, name FROM students").fetchall()
    conn.close()
    return {int(s["student_id"]): s["name"] for s in students}


student_map = get_student_map()
today_date = datetime.now().strftime("%Y-%m-%d")


# ---------- Step 6: Mark Attendance ----------
def mark_attendance(student_id_string):
    """Update status from Absent → Present when recognized."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today_date = datetime.now().strftime("%Y-%m-%d")

    # Get internal id + admin_id
    c.execute("SELECT id, admin_id FROM students WHERE student_id=?", (str(student_id_string),))
    row = c.fetchone()
    if not row:
        conn.close()
        return False

    db_pk, admin_id = row

    # Check today's record
    c.execute("SELECT status FROM attendance WHERE student_id=? AND date=? AND admin_id=?",
              (db_pk, today_date, admin_id))
    record = c.fetchone()

    if record:
        if record[0] == "Absent":
            # Update Absent → Present
            c.execute("""
                UPDATE attendance SET status='Present'
                WHERE student_id=? AND date=? AND admin_id=?
            """, (db_pk, today_date, admin_id))
            conn.commit()
            conn.close()
            return True
        elif record[0] == "Present":
            conn.close()
            return False
    else:
        # If no record exists, create new
        c.execute("""
            INSERT INTO attendance (student_id, date, status, admin_id)
            VALUES (?, ?, ?, ?)
        """, (db_pk, today_date, "Present", admin_id))
        conn.commit()
        conn.close()
        return True


# ---------- Step 7: Voice Functions ----------
def record_voice_temp(duration=3, samplerate=16000):
    print("[INFO] Please speak...")
    rec = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    tmp = os.path.join(BASE_DIR, "temp_voice.wav")
    sf.write(tmp, rec, samplerate)
    return tmp


def voice_similarity(file1, file2):
    try:
        y1, sr1 = librosa.load(file1, sr=16000)
        y2, sr2 = librosa.load(file2, sr=16000)
        mf1 = librosa.feature.mfcc(y=y1, sr=sr1, n_mfcc=20)
        mf2 = librosa.feature.mfcc(y=y2, sr=sr2, n_mfcc=20)
        v1 = np.mean(mf1, axis=1)
        v2 = np.mean(mf2, axis=1)
        return 1 - cosine(v1, v2)
    except Exception as e:
        print("[WARN] Voice compare failed:", e)
        return 0


# ---------- Step 8: Start Recognition ----------
mark_all_absent()  # ✅ Initialize Absent (only once per day)

cap = cv2.VideoCapture(0)
window = "SmartAttendX - Face & Voice Recognition"
print("[INFO] Press 'q' to quit.")

processed = set()  # track faces processed this session
pending_student = None
last_prompt_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    display_frame = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(80, 80))

    for (x, y, w, h) in faces:
        face_img = gray[y:y + h, x:x + w]
        face_resized = cv2.resize(face_img, (200, 200))

        if recognizer is None:
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 165, 255), 2)
            cv2.putText(display_frame, "Model missing", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            continue

        label, confidence = recognizer.predict(face_resized)
        if confidence < 55:
            db_id = int(label)
            name = student_map.get(db_id, "Unknown")

            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(display_frame, f"Roll {db_id} {name}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            if db_id not in processed and pending_student is None:
                pending_student = db_id
                last_prompt_time = time.time()

                engine.stop()
                engine.say("Please speak hello to mark your attendance")
                engine.runAndWait()
        else:
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # ---------- Voice verification ----------
    if pending_student is not None and time.time() - last_prompt_time > 1:
        db_id = pending_student
        name = student_map.get(db_id, "Unknown")
        voice_saved = os.path.join(TRAINED_DIR, str(db_id), "voice.wav")
        marked_msg = ""

        if os.path.exists(voice_saved):
            temp_file = record_voice_temp(duration=3)
            sim = voice_similarity(voice_saved, temp_file)
            print(f"[INFO] Voice similarity: {sim:.2f}")
            if sim >= 0.75:
                if mark_attendance(db_id):
                    marked_msg = f"Attendance marked for roll no {db_id} {name}"
                else:
                    marked_msg = f"Attendance already marked for roll no {db_id} {name}"
            else:
                marked_msg = "Voice mismatch. Attendance not marked."
        else:
            if mark_attendance(db_id):
                marked_msg = f"Attendance marked for roll no {db_id} {name}"
            else:
                marked_msg = f"Attendance already marked for roll no {db_id} {name}"

        print("✅", marked_msg)
        engine.stop()
        engine.say(marked_msg)
        engine.runAndWait()

        processed.add(db_id)
        pending_student = None

    cv2.imshow(window, display_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
print("👋 Stopped.")
