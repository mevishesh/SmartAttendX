import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # ✅ fixed here
DB_PATH = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Admins table
# c.execute("""
# CREATE TABLE IF NOT EXISTS admins (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL,
#     email TEXT NOT NULL UNIQUE,
#     password TEXT NOT NULL
# )
# """)
c.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    profile_pic TEXT
)
""")

# Students table (linked to admin)
c.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    roll_no TEXT,
    name TEXT NOT NULL,
    email TEXT,
    guardian_no TEXT,
    guardian_email TEXT,
    admin_id INTEGER NOT NULL,
    FOREIGN KEY(admin_id) REFERENCES admins(id)
)
""")

# ✅ ensure new columns exist even if table already created
# (SQLite ignores duplicate column adds)
try:
    c.execute("ALTER TABLE students ADD COLUMN roll_no TEXT;")
except sqlite3.OperationalError:
    pass  # column already exists

try:
    c.execute("ALTER TABLE students ADD COLUMN guardian_email TEXT;")
except sqlite3.OperationalError:
    pass  # column already exists

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
