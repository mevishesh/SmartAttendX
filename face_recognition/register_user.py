import cv2
import os
import numpy as np
from PIL import Image
import time

# ➕ Create the folder if it doesn't exist
TRAINED_FACES_DIR = os.path.join(os.path.dirname(__file__), "trained_faces")
if not os.path.exists(TRAINED_FACES_DIR):
    os.makedirs(TRAINED_FACES_DIR)

# ✅ Load Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# 💡 Function to train and save recognizer after collecting images
def train_model():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces, ids = [], []

    for folder_name in os.listdir(TRAINED_FACES_DIR):
        folder_path = os.path.join(TRAINED_FACES_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        for filename in os.listdir(folder_path):
            if filename.endswith(".jpg"):
                path = os.path.join(folder_path, filename)
                image = Image.open(path).convert("L")
                img_np = np.array(image, "uint8")
                id_num = int(folder_name)  # folder is student_id
                faces.append(img_np)
                ids.append(id_num)

    if len(faces) == 0:
        print("[WARN] No faces found to train.")
        return

    recognizer.train(faces, np.array(ids))
    recognizer.save(os.path.join(TRAINED_FACES_DIR, "face_model.yml"))
    print("✅ Face model trained and saved.")

# 🚀 Main function to capture face images
def capture_faces(student_id):
    save_path = os.path.join(TRAINED_FACES_DIR, str(student_id))
    os.makedirs(save_path, exist_ok=True)

    cap = cv2.VideoCapture(0)
    count = 0

    print("[INFO] Starting face capture. Look at the camera...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            count += 1
            face_img = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_img, (200, 200))
            file_name = os.path.join(save_path, f"{count}.jpg")
            cv2.imwrite(file_name, face_resized)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.imshow("Capturing Faces", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        elif count >= 20:
            break

    print(f"[INFO] {count} face images saved to {save_path}")
    cap.release()
    cv2.destroyAllWindows()

    # 👇 Retrain model with new student
    train_model()

# 🧾 Start here
if __name__ == "__main__":
    student_id = input("Enter numeric Student ID: ")
    if not student_id.isdigit():
        print("[ERROR] Student ID must be numeric.")
    else:
        capture_faces(student_id)
