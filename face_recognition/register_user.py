#!/usr/bin/env python3

import sys, os, time, cv2, numpy as np, sqlite3
from PIL import Image
import tkinter as tk
from tkinter import messagebox

# Audio
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False

# TTS
try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "database.db")
TRAINED_DIR = os.path.join(BASE_DIR, "trained_faces")
MODEL_PATH = os.path.join(TRAINED_DIR, "face_model.yml")
os.makedirs(TRAINED_DIR, exist_ok=True)

NUM_IMAGES = 20
INTERVAL = 1.0
WARMUP_TIME = 5
VOICE_DURATION = 4
SAMPLE_RATE = 16000

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def show_popup(title, message, is_error=False):
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    if is_error:
        messagebox.showerror(title, message)
    else:
        messagebox.showinfo(title, message)
    root.destroy()

def speak(text):
    if not TTS_AVAILABLE: return
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        show_popup("Warning", f"Could not speak: {e}", is_error=True)

def record_voice(save_path, duration=4, samplerate=16000):
    if not AUDIO_AVAILABLE:
        show_popup("Info", "Audio libraries missing; skipping voice sample.")
        return
    try:
        msg = "Please say: Hi, my name is, and then your name."
        show_popup("Voice Recording", f"Recording voice. {msg}")
        speak(msg)
        recording = sd.rec(int(duration * samplerate),
                           samplerate=samplerate,
                           channels=1, dtype='int16')
        sd.wait()
        sf.write(save_path, recording, samplerate)
        show_popup("Success", f"Voice saved at {save_path}")
    except Exception as e:
        show_popup("Warning", f"Voice record failed: {e}", is_error=True)

def train_model():
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except:
        show_popup("Error", "Install opencv-contrib-python for LBPH", is_error=True)
        return
    faces, ids = [], []
    for folder in os.listdir(TRAINED_DIR):
        folder_path = os.path.join(TRAINED_DIR, folder)
        if not os.path.isdir(folder_path): continue
        for fname in os.listdir(folder_path):
            if fname.lower().endswith((".jpg",".jpeg",".png")):
                path = os.path.join(folder_path,fname)
                try:
                    img = Image.open(path).convert("L")
                    img_np = cv2.equalizeHist(np.array(img,"uint8"))
                    faces.append(img_np)
                    ids.append(int(folder))
                except Exception as e:
                    show_popup("Warning", f"Skipping {path}: {e}", is_error=True)
    if not faces:
        show_popup("Warning", "No faces found. Model not saved.")
        return
    recognizer.train(faces,np.array(ids))
    recognizer.save(MODEL_PATH)
    show_popup("Success", f"Model trained & saved to {MODEL_PATH} with {len(faces)} images.")

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
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        show_popup("Error", "Cannot open webcam.", is_error=True)
        return False

    cv2.namedWindow(f"Registering {student_id}", cv2.WINDOW_AUTOSIZE)

    show_popup("Info", f"Warming up camera, scanning face for {WARMUP_TIME} seconds...")
    warm_start = time.time()
    while time.time() - warm_start < WARMUP_TIME:
        ret, frame = cap.read()
        if not ret: continue
        cv2.putText(frame, "Analyzing face...", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.imshow(f"Registering {student_id}", frame)
        if cv2.waitKey(1)&0xFF==ord('q'):break

    show_popup("Info", f"Capturing {NUM_IMAGES} faces for student {student_id}")
    count=0;last=0
    while count<NUM_IMAGES:
        ret,frame=cap.read()
        if not ret: continue
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        faces=face_cascade.detectMultiScale(gray,1.2,5,minSize=(80,80))
        if len(faces)>0 and time.time()-last>=INTERVAL:
            (x,y,w,h)=max(faces,key=lambda r:r[2]*r[3])
            face=cv2.resize(frame[y:y+h,x:x+w],(200,200))
            file_path=os.path.join(save_dir,f"{count+1}.jpg")
            cv2.imwrite(file_path,face)
            count+=1;last=time.time()
            cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.putText(frame, f"Capturing {count}/{NUM_IMAGES}", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.imshow(f"Registering {student_id}",frame)
        if cv2.waitKey(1)&0xFF==ord('q'):break

    cap.release();cv2.destroyAllWindows()
    if count==0:
        show_popup("Error", f"Failed to capture any faces.", is_error=True)
        return False

    record_voice(os.path.join(save_dir,"voice.wav"),
                 duration=VOICE_DURATION,samplerate=SAMPLE_RATE)
    train_model()
    return True
if __name__ == "__main__":
    if len(sys.argv) == 7:
        student_id     = sys.argv[1]
        name           = sys.argv[2]
        roll_no        = sys.argv[3]
        email          = sys.argv[4]
        guardian_no    = sys.argv[5]
        guardian_email = sys.argv[6]
    else:
        show_popup("Error", "Incorrect number of arguments. Please register from the web portal.", is_error=True)
        sys.exit(1)

    if not student_id.isdigit():
        show_popup("Error", "Student ID must be numeric.", is_error=True)
        sys.exit(1)

    insert_student(student_id, name, roll_no, email, guardian_no, guardian_email)

    if capture_faces(student_id):
        show_popup("Success", f"Registration complete for {name} (Roll {roll_no})")
    else:
        show_popup("Error", "Registration failed.", is_error=True)