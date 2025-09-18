#!/usr/bin/env python3
import os
import shutil
import sqlite3

print("⚠ WARNING: This will DELETE ALL student data and images. Type 'YES' to continue:", end=" ")
confirm = input().strip()

if confirm != "YES":
    print("❌ Aborted.")
    exit(0)

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # face_recognition folder
DB_PATH = os.path.join(BASE_DIR, "..", "database", "database.db")
TRAINED_DIR = os.path.join(BASE_DIR, "trained_faces")

# Remove database
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
        print(f"✅ Database removed: {DB_PATH}")
    except Exception as e:
        print(f"[ERROR] Could not remove database: {e}")
else:
    print("[WARN] Database not found. Skipping database clearing.")

# Remove trained faces
if os.path.exists(TRAINED_DIR):
    try:
        shutil.rmtree(TRAINED_DIR)
        print(f"✅ Trained faces folder removed: {TRAINED_DIR}")
    except Exception as e:
        print(f"[ERROR] Could not remove trained faces: {e}")
else:
    print("[WARN] Trained faces folder not found. Skipping images clearing.")

print("✅ Reset complete.")
