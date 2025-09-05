import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # ✅ fixed here
DB_PATH = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Admins table
c.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
""")

# Students table (linked to admin)
c.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    guardian_no TEXT,
    admin_id INTEGER NOT NULL,
    FOREIGN KEY(admin_id) REFERENCES admins(id)
)
""")

# Attendance table
c.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    admin_id INTEGER,
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(admin_id) REFERENCES admins(id)
)
""")

# ➕ Add a unique index so only one attendance per student per date
c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_student_date
ON attendance(student_id, date)
""")

conn.commit()
conn.close()

print(f"✅ Database created/updated successfully at: {DB_PATH}")
