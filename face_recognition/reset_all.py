#!/usr/bin/env python3
import os, sqlite3, shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # face_recognition folder
DB_PATH = os.path.join(BASE_DIR, "..", "database", "database.db")
TRAINED_DIR = os.path.join(BASE_DIR, "trained_faces")

print("Choose what you want to delete:")
print("1. Clear only attendance history")
print("2. Clear all students but keep admins")
print("3. Clear all admins (and everything)")
print("4. Clear trained faces folder")
print("5. Clear EVERYTHING (database + faces)")
choice = input("Enter choice (1-5): ").strip()

conn = None
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)

if choice == "1":
    if conn:
        conn.execute("DELETE FROM attendance;")
        conn.commit()
        print("✅ All attendance history cleared.")
elif choice == "2":
    if conn:
        conn.execute("DELETE FROM students;")
        conn.execute("DELETE FROM attendance;")
        conn.commit()
        print("✅ All students & their attendance cleared.")
elif choice == "3":
    if conn:
        conn.execute("DELETE FROM admins;")
        conn.execute("DELETE FROM students;")
        conn.execute("DELETE FROM attendance;")
        conn.commit()
        print("✅ All admins, students & attendance cleared.")
elif choice == "4":
    if os.path.exists(TRAINED_DIR):
        shutil.rmtree(TRAINED_DIR)
        print(f"✅ Trained faces folder removed: {TRAINED_DIR}")
    else:
        print("[WARN] No trained faces folder found.")
elif choice == "5":
    if os.path.exists(DB_PATH):
        conn.close()
        os.remove(DB_PATH)
        print(f"✅ Database removed: {DB_PATH}")
    if os.path.exists(TRAINED_DIR):
        shutil.rmtree(TRAINED_DIR)
        print(f"✅ Trained faces folder removed: {TRAINED_DIR}")
    print("✅ Everything wiped.")
else:
    print("❌ Invalid choice.")

if conn:
    conn.close()
