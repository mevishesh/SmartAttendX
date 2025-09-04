from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import subprocess
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "database.db")


# ---------- Database Helper ----------
def init_db():
    """Ensure required tables exist"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Admins table
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Students table
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            roll_no TEXT,
            guardian_no TEXT,
            admin_id INTEGER,
            FOREIGN KEY(admin_id) REFERENCES admins(id)
        )
    """)

    # Attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            admin_id INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(admin_id) REFERENCES admins(id)
        )
    """)

    conn.commit()
    conn.close()


# Call init_db at startup
init_db()


def is_logged_in():
    return "admin_id" in session


# ---------- Routes ----------

# Landing Page
@app.route("/")
def home():
    return render_template("index.html")


# Login API
@app.route("/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            return jsonify({"success": "Login successful"})
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print("❌ Login error:", str(e))
        return jsonify({"error": "Server error during login"}), 500


# Login Page
@app.route("/login-page")
def login_page():
    return render_template("login.html")


# Register API
@app.route("/register", methods=["POST"])
def api_register():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check if email already exists
        c.execute("SELECT id FROM admins WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({"error": "Email already registered"}), 400

        c.execute("INSERT INTO admins (name, email, password) VALUES (?, ?, ?)",
                  (name, email, password))
        conn.commit()
        conn.close()
        return jsonify({"success": "Account created successfully!"})
    except Exception as e:
        print("❌ Registration error:", str(e))
        return jsonify({"error": "Server error during registration"}), 500


# Register Page
@app.route("/register-page")
def register_page():
    return render_template("register.html")


# Dashboard
@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all students of this admin
    c.execute("SELECT * FROM students WHERE admin_id = ?", (session["admin_id"],))
    students = c.fetchall()

    # Attendance counts
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND admin_id = ?", (today, session["admin_id"]))
    present_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM students WHERE admin_id = ?", (session["admin_id"],))
    total_students = c.fetchone()[0]
    absent_count = total_students - present_count

    conn.close()

    return render_template(
        "dashboard.html",
        students=students,
        admin_name=session.get("admin_name", "Admin"),
        present_count=present_count,
        absent_count=absent_count,
    )


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# Start Face Attendance
@app.route("/start-attendance", methods=["POST"])
def start_attendance():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    try:
        subprocess.Popen(["python", "face_recognition/recognizer.py"])
        return redirect(url_for("dashboard"))
    except Exception as e:
        print("❌ Attendance start error:", str(e))
        return jsonify({"error": "Could not start recognizer"}), 500


# Register New Student
@app.route("/register-student", methods=["POST"])
def register_student():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    student_id = request.form.get("student_id")
    name = request.form.get("name")
    email = request.form.get("email")
    roll_no = request.form.get("roll_no")
    guardian_no = request.form.get("guardian_no")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO students (student_id, name, email, roll_no, guardian_no, admin_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, name, email, roll_no, guardian_no, session["admin_id"]))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# Notify Students
@app.route("/notify", methods=["POST"])
def notify():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    target = request.form.get("target")
    message = request.form.get("message")

    # For now, just print to console (can extend to email/SMS)
    print(f"📢 Notification to {target}: {message}")

    return redirect(url_for("dashboard"))

# Student Attendance History
@app.route("/attendance-history/<int:student_id>")
def attendance_history(student_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch student info
    c.execute("SELECT * FROM students WHERE id = ? AND admin_id = ?", (student_id, session["admin_id"]))
    student = c.fetchone()

    if not student:
        conn.close()
        return "Student not found or unauthorized", 404

    # Fetch attendance records
    c.execute("SELECT date, status FROM attendance WHERE student_id = ? AND admin_id = ? ORDER BY date DESC",
              (student_id, session["admin_id"]))
    records = c.fetchall()
    conn.close()

    return render_template("attendance_history.html", student=student, records=records)

# ---------- Main ----------
if __name__ == "__main__":
    app.run(debug=True)
