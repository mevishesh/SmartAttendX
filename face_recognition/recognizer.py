import cv2
import numpy as np
import os
import sqlite3
from datetime import datetime
import pyttsx3

# --------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "../database/database.db")
MODEL_PATH = os.path.join(BASE_DIR, "trained_faces/face_model.yml")

# --------- Load model ----------
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

# --------- Load cascade ----------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# --------- Text-to-speech ----------
engine = pyttsx3.init()

# --------- Load student map ----------
def get_student_map():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    students = c.execute("SELECT id, name FROM students").fetchall()
    conn.close()
    return {s["id"]: s["name"] for s in students}

student_map = get_student_map()

# --------- Attendance function ----------
today_date = datetime.now().strftime("%Y-%m-%d")
# recognizer.py

def mark_attendance(student_id):
    """
    Returns True if new attendance inserted,
    False if already marked for today.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Find the admin_id of this student
    c.execute("SELECT admin_id FROM students WHERE id=?", (student_id,))
    row = c.fetchone()
    admin_id = row[0] if row else None

    c.execute("SELECT 1 FROM attendance WHERE student_id=? AND date=? AND admin_id=?",
              (student_id, today_date, admin_id))
    already = c.fetchone()
    if not already:
        c.execute("INSERT INTO attendance (student_id, date, status, admin_id) VALUES (?,?,?,?)",
                  (student_id, today_date, "Present", admin_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


# --------- Start recognition ----------
cap = cv2.VideoCapture(0)
window_name = "SmartAttendX - Face Recognition"
print("[INFO] Starting face recognition... Press 'q' to quit or close the window.")

spoken_counts = {}  # how many times we’ve spoken per student this run
MAX_SPEAKS = 1      # speak once per student per run

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces:
        face_img = gray[y:y + h, x:x + w]
        face_resized = cv2.resize(face_img, (200, 200))

        label, confidence = recognizer.predict(face_resized)

        if confidence < 50:  # good confidence
            roll_no = label
            name = student_map.get(label, "Unknown")

            cv2.putText(frame, f"Roll:{roll_no} {name}",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            count = spoken_counts.get(roll_no, 0)
            if count < MAX_SPEAKS:
                if mark_attendance(roll_no):
                    msg = f"Attendance marked for roll number {roll_no}"
                else:
                    msg = f"Attendance already marked today for roll number {roll_no}"
                print("✅ " + msg)
                engine.say(msg)
                engine.runAndWait()
                spoken_counts[roll_no] = count + 1
        else:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

    cv2.imshow(window_name, frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
print("👋 Face recognition stopped.")
