#!/usr/bin/env python3
import sys, os, time, cv2, numpy as np, sqlite3
from PIL import Image
import tkinter as tk
from tkinter import messagebox

# Simple audio record
import sounddevice as sd
import soundfile as sf

# Text-to-speech (optional)
try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "database.db")
TRAINED_DIR = os.path.join(BASE_DIR, "trained_faces")
os.makedirs(TRAINED_DIR, exist_ok=True)

NUM_IMAGES = 20
INTERVAL = 1.0
WARMUP_TIME = 5
VOICE_DURATION = 3
SAMPLE_RATE = 16000

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def show_popup(title, message, is_error=False):
    root = tk.Tk()
    root.withdraw()
    if is_error:
        messagebox.showerror(title, message)
    else:
        messagebox.showinfo(title, message)
    root.destroy()

def speak(text):
    if TTS_AVAILABLE:
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

def record_voice(save_path):
    """Record short 3s voice sample"""
    show_popup("Voice Recording", "Recording will start in 2 seconds.\nPlease say 'Hello'.")
    speak("Please say Hello")
    time.sleep(2)
    try:
        rec = sd.rec(int(VOICE_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        sf.write(save_path, rec, SAMPLE_RATE)
        show_popup("Voice Saved", f"Voice sample saved at {save_path}")
        return True
    except Exception as e:
        show_popup("Error", f"Voice recording failed: {e}", is_error=True)
        return False

def insert_student(student_id, name, roll_no, email, guardian_no, guardian_email, admin_id=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO students (student_id, name, roll_no, email, guardian_no, guardian_email, admin_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_id, name, roll_no, email, guardian_no, guardian_email, admin_id))
    conn.commit()
    conn.close()

def capture_faces(student_id):
    save_dir = os.path.join(TRAINED_DIR, str(student_id))
    os.makedirs(save_dir, exist_ok=True)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        show_popup("Error", "Cannot open webcam.", is_error=True)
        return False

    window_name = f"Registering {student_id}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 800, 600)

    show_popup("Info", f"Warming up camera for {WARMUP_TIME} seconds...")
    warm_start = time.time()
    while time.time() - warm_start < WARMUP_TIME:
        ret, frame = cap.read()
        if not ret: continue
        cv2.putText(frame, "Initializing camera...", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    show_popup("Info", f"Capturing {NUM_IMAGES} face samples...")
    count, last = 0, 0
    while count < NUM_IMAGES:
        ret, frame = cap.read()
        if not ret: continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80, 80))
        if len(faces) > 0 and time.time() - last >= INTERVAL:
            (x, y, w, h) = max(faces, key=lambda r: r[2] * r[3])
            face = frame[y:y+h, x:x+w]
            file_path = os.path.join(save_dir, f"{count+1}.jpg")
            cv2.imwrite(file_path, face)
            count += 1
            last = time.time()
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cv2.putText(frame, f"Captured {count}/{NUM_IMAGES}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

    if count == 0:
        show_popup("Error", "No faces captured.", is_error=True)
        return False

    voice_path = os.path.join(save_dir, "voice.wav")
    record_voice(voice_path)
    return True

if __name__ == "__main__":
    if len(sys.argv) == 7:
        student_id = sys.argv[1]
        name = sys.argv[2]
        roll_no = sys.argv[3]
        email = sys.argv[4]
        guardian_no = sys.argv[5]
        guardian_email = sys.argv[6]
    else:
        show_popup("Error", "Incorrect arguments. Register via web portal.", is_error=True)
        sys.exit(1)

    insert_student(student_id, name, roll_no, email, guardian_no, guardian_email)

    if capture_faces(student_id):
        show_popup("Success", f"Registration complete for {name}")
    else:
        show_popup("Error", "Registration failed.", is_error=True)
