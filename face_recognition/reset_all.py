import os
import shutil
import sqlite3

# === Adjust these paths to your project ===
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
faces_dir = os.path.join(base_dir, "face_recognition", "trained_faces")
model_file = os.path.join(base_dir, "face_recognition", "face_model.yml")
db_path = os.path.join(base_dir, "database", "database.db")

# 1. Remove trained_faces folder contents
if os.path.exists(faces_dir):
    shutil.rmtree(faces_dir)
    print("✅ Deleted trained_faces folder")
os.makedirs(faces_dir, exist_ok=True)

# 2. Remove model file
if os.path.exists(model_file):
    os.remove(model_file)
    print("✅ Deleted face_model.yml")

# 3. Clear records from database tables (students + attendance)
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("DELETE FROM attendance;")
    c.execute("DELETE FROM students;")
    conn.commit()
    conn.close()
    print(f"✅ Cleared students and attendance tables from {db_path}")
else:
    print(f"⚠ Database file not found at {db_path}")

print("🎯 All training images, model file, and DB records cleared successfully")