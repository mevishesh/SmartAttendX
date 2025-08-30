import cv2
import numpy as np
import os
import sqlite3
from datetime import datetime

# 📌 DB Path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/database.db"))

# 📁 Face model path
MODEL_PATH = os.path.join(os.path.dirname(__file__), "trained_faces/face_model.yml")

# 📁 Load model
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

# 📷 Load face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# 🧠 Load student mapping (ID → Name)
def get_student_map():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    students = c.execute("SELECT id, name FROM students").fetchall()
    conn.close()
    return {s["id"]: s["name"] for s in students}

student_map = get_student_map()

# 🕒 Today's date
today_date = datetime.now().strftime("%Y-%m-%d")

# 📝 Mark attendance
def mark_attendance(student_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if already marked today
    c.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?", (student_id, today_date))
    already = c.fetchone()

    if not already:
        c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (student_id, today_date, "Present"))
        conn.commit()
        print(f"✅ Attendance marked for: {student_map.get(student_id)}")
    else:
        print(f"ℹ️ Already marked today for: {student_map.get(student_id)}")

    conn.close()

# 🚀 Start recognition
cap = cv2.VideoCapture(0)
print("[INFO] Starting face recognition... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face_img = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_img, (200, 200))

        label, confidence = recognizer.predict(face_resized)

        if confidence < 50:  # lower = more confident
            name = student_map.get(label, "Unknown")
            mark_attendance(label)
            cv2.putText(frame, f"{name}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            color = (0, 255, 0)
        else:
            cv2.putText(frame, "Unknown", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            color = (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

    cv2.imshow("SecureAttendX - Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("👋 Face recognition stopped.")
