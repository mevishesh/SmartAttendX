#!/usr/bin/env python3
import os, time, cv2, numpy as np, sqlite3
from datetime import datetime
import face_recognition
import sounddevice as sd
import soundfile as sf
import librosa
from scipy.spatial.distance import cosine

# Optional text-to-speech
try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "database.db")
TRAINED_DIR = os.path.join(BASE_DIR, "trained_faces")
os.makedirs(TRAINED_DIR, exist_ok=True)

FACE_DISTANCE_THRESHOLD = 0.6
VOICE_SIM_THRESHOLD = 0.75
VOICE_DURATION = 3
SAMPLE_RATE = 16000

def speak(text):
    if TTS_AVAILABLE:
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

def mark_attendance_db_by_student_internal_id(db_pk, admin_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM attendance WHERE student_id=? AND date=? AND admin_id=?",
              (db_pk, today, admin_id))
    r = c.fetchone()
    if r:
        if r[0] == "Absent":
            c.execute("UPDATE attendance SET status='Present' WHERE student_id=? AND date=? AND admin_id=?",
                      (db_pk, today, admin_id))
            conn.commit()
        conn.close()
        return False
    else:
        c.execute("INSERT INTO attendance (student_id, date, status, admin_id) VALUES (?, ?, ?, ?)",
                  (db_pk, today, "Present", admin_id))
        conn.commit()
        conn.close()
        return True

def get_students_face_embeddings():
    embeddings = {}
    for folder in os.listdir(TRAINED_DIR):
        folder_path = os.path.join(TRAINED_DIR, folder)
        if not os.path.isdir(folder_path): continue
        sid = folder
        faces = []
        for fname in os.listdir(folder_path):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(folder_path, fname)
                img = cv2.imread(path)
                if img is None: continue
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                locs = face_recognition.face_locations(rgb)
                encs = face_recognition.face_encodings(rgb, locs)
                if encs: faces.append(encs[0])
        if faces:
            embeddings[int(sid)] = faces
            print(f"[INFO] Loaded {len(faces)} faces for {sid}")
    return embeddings

def build_student_lookup():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, student_id, name, admin_id FROM students")
    data = c.fetchall()
    conn.close()
    lookup = {}
    for row in data:
        lookup[int(row[1])] = {"db_pk": row[0], "name": row[2], "admin_id": row[3]}
    return lookup

def record_voice_temp():
    tmp_path = os.path.join(BASE_DIR, "temp_voice.wav")
    speak("Please say hello")
    print("[INFO] Recording 3 seconds voice...")
    rec = sd.rec(int(VOICE_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    sf.write(tmp_path, rec, SAMPLE_RATE)
    return tmp_path

def compare_voice(saved_path, new_path):
    try:
        y1, sr1 = librosa.load(saved_path, sr=16000)
        y2, sr2 = librosa.load(new_path, sr=16000)
        mf1 = librosa.feature.mfcc(y=y1, sr=sr1, n_mfcc=20)
        mf2 = librosa.feature.mfcc(y=y2, sr=sr2, n_mfcc=20)
        v1 = np.mean(mf1, axis=1)
        v2 = np.mean(mf2, axis=1)
        sim = 1 - cosine(v1, v2)
        print(f"[VOICE SIMILARITY] {sim:.2f}")
        return sim >= VOICE_SIM_THRESHOLD
    except Exception as e:
        print("[Voice ERROR]", e)
        return False

# Load data
face_db = get_students_face_embeddings()
student_lookup = build_student_lookup()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Could not open camera.")
    exit()

print("[INFO] Face recognizer started. Press 'q' to exit.")
cv2.namedWindow("SmartAttendX - Recognition", cv2.WINDOW_NORMAL)
cv2.resizeWindow("SmartAttendX - Recognition", 800, 600)

processed_today = set()

while True:
    ret, frame = cap.read()
    if not ret: continue
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb)
    encs = face_recognition.face_encodings(rgb, locs)

    for (top, right, bottom, left), enc in zip(locs, encs):
        best_sid, best_dist = None, 1.0
        for sid, embs in face_db.items():
            dists = [np.linalg.norm(enc - e) for e in embs]
            if dists:
                d = min(dists)
                if d < best_dist:
                    best_dist, best_sid = d, sid

        if best_sid and best_dist <= FACE_DISTANCE_THRESHOLD:
            info = student_lookup.get(best_sid)
            name = info["name"]
            cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
            cv2.putText(frame, f"{name} ({best_sid})", (left, top-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            if best_sid not in processed_today:
                saved_voice = os.path.join(TRAINED_DIR, str(best_sid), "voice.wav")
                if os.path.exists(saved_voice):
                    temp_path = record_voice_temp()
                    if compare_voice(saved_voice, temp_path):
                        mark_attendance_db_by_student_internal_id(info["db_pk"], info["admin_id"])
                        speak(f"Attendance marked for {name}")
                        print(f"[OK] Attendance marked for {name}")
                    else:
                        speak("Voice mismatch")
                        print("[WARN] Voice mismatch")
                else:
                    mark_attendance_db_by_student_internal_id(info["db_pk"], info["admin_id"])
                    print(f"[OK] Attendance marked (no voice sample) for {name}")
                processed_today.add(best_sid)
        else:
            cv2.rectangle(frame, (left, top), (right, bottom), (0,0,255), 2)
            cv2.putText(frame, "Unknown", (left, top-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

    cv2.imshow("SmartAttendX - Recognition", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("[INFO] Recognition stopped.")
