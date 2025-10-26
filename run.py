from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
import sqlite3
import os
import sys
import platform
import subprocess
from datetime import datetime, timedelta
import shutil
from flask_mail import Mail, Message

# ---------------- App Setup ----------------
app = Flask(__name__)
app.secret_key = "your-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "database.db")

# ---------------- Mail Configuration ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "smartattendx@gmail.com"        # sender Gmail
app.config['MAIL_PASSWORD'] = "xadq ichq urrr ponl"           # Gmail app password
app.config['MAIL_DEFAULT_SENDER'] = "smartattendx@gmail.com"

mail = Mail(app)

# ---------------- Paths ----------------
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- Database Initialization ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_pic TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            roll_no TEXT,
            guardian_no TEXT,
            guardian_email TEXT,
            admin_id INTEGER,
            FOREIGN KEY(admin_id) REFERENCES admins(id)
        )
    """)

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

init_db()

# ---------------- Helpers ----------------
def is_logged_in():
    return "admin_id" in session

def query_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return user

# ---------------- Routes ----------------

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def home():
    return render_template("index.html")

# ---- Login ----
@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = query_user_by_email(email)
    if user and user["password"] == password:
        session["admin_id"] = user["id"]
        session["admin_email"] = user["email"]
        session["admin_name"] = user["name"]
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Invalid email or password"})

@app.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(url_for("login_page")))
    return resp

# ---- Register ----
@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True)
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""

        if not name or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM admins WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return jsonify({"error": "Email already registered"}), 400

        c.execute("INSERT INTO admins (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        conn.close()
        return jsonify({"success": "Account created successfully!"})
    except Exception as e:
        print("❌ Registration error:", str(e))
        return jsonify({"error": "Server error during registration"}), 500

# ---- Profile ----
@app.route("/profile")
def profile():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],))
    admin = c.fetchone()
    conn.close()

    return render_template("profile.html", admin=admin)

@app.route("/update-profile", methods=["POST"])
def update_profile():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    profile_pic = request.files.get("profile_pic")

    pic_rel_url = None
    if profile_pic and profile_pic.filename:
        filename = f"profile_{session['admin_id']}.png"
        save_path = os.path.join(UPLOAD_DIR, filename)
        profile_pic.save(save_path)
        pic_rel_url = f"uploads/{filename}".replace("\\", "/")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if pic_rel_url:
        c.execute("UPDATE admins SET name=?, email=?, profile_pic=? WHERE id=?", (name, email, pic_rel_url, session["admin_id"]))
    else:
        c.execute("UPDATE admins SET name=?, email=? WHERE id=?", (name, email, session["admin_id"]))
    conn.commit()
    conn.close()

    session["admin_name"] = name
    flash("Profile updated successfully.", "success")
    return redirect(url_for("profile"))

# ---- Dashboard ----
@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],))
    admin = c.fetchone()

    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT * FROM students WHERE admin_id = ?", (session["admin_id"],))
    students = c.fetchall()

    c.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present' AND admin_id=?", (today, session["admin_id"]))
    present_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent' AND admin_id=?", (today, session["admin_id"]))
    absent_count = c.fetchone()[0]

    attendance_records = c.execute("""
        SELECT a.id, a.student_id, s.name, s.roll_no, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.admin_id = ?
        ORDER BY a.date DESC
    """, (session["admin_id"],)).fetchall()

    attendance_records = [dict(zip(['id','student_id','name','roll_no','date','status'], row)) for row in attendance_records]

    conn.close()

    return render_template(
        "dashboard.html",
        admin=admin,
        present_count=present_count,
        absent_count=absent_count,
        total_students=students,
        attendance_records=attendance_records,
        datetime=datetime
    )

# ---- Delete Student ----
@app.route("/delete-student/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
        c.execute("DELETE FROM students WHERE id=?", (student_id,))
        conn.commit()
        conn.close()

        trained_faces_dir = os.path.join(BASE_DIR, "face_recognition", "trained_faces", str(student_id))
        if os.path.isdir(trained_faces_dir):
            shutil.rmtree(trained_faces_dir)
            print(f"✅ Deleted folder: {trained_faces_dir}")

        return jsonify({"success": "Student deleted successfully!"})
    except Exception as e:
        print("[ERROR] Delete student failed:", e)
        return jsonify({"error": "Server error while deleting."}), 500

# ---- Start Attendance ----
@app.route("/start-attendance", methods=["POST"])
def start_attendance():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    try:
        script_path = os.path.join(BASE_DIR, "face_recognition", "recognizer.py")
        popen_kwargs = {}
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        subprocess.Popen([sys.executable, script_path], **popen_kwargs)
        flash("Recognizer started.", "info")
        return redirect(url_for("dashboard"))
    except Exception as e:
        print("❌ Attendance start error:", str(e))
        return jsonify({"error": "Could not start recognizer"}), 500

# ---- Register Student ----
@app.route("/register-student", methods=["POST"])
def register_student():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    student_id = request.form.get("student_id", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    roll_no = request.form.get("roll_no", "").strip()
    guardian_no = request.form.get("guardian_no", "").strip()
    guardian_email = request.form.get("guardian_email", "").strip()

    if not student_id or not name:
        flash("Student ID and Name are required", "warning")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM students WHERE student_id=?", (student_id,))
    existing = c.fetchone()
    if existing:
        conn.close()
        flash(f"⚠ Student ID {student_id} already exists.", "warning")
        return redirect(url_for("dashboard"))

    c.execute("""
        INSERT INTO students (student_id, name, email, roll_no, guardian_no, guardian_email, admin_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_id, name, email, roll_no, guardian_no, guardian_email, session["admin_id"]))
    conn.commit()
    conn.close()

    try:
        script_path = os.path.join(BASE_DIR, "face_recognition", "register_user.py")
        popen_kwargs = {}
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

        subprocess.Popen([sys.executable, script_path, student_id, name, roll_no, email, guardian_no, guardian_email], **popen_kwargs)
        flash(f"✅ Student {name} added. Starting face capture…", "success")
    except Exception as e:
        print("[ERROR] Could not start register_user.py:", e)
        flash("Student added but could not start face capture script.", "danger")

    return redirect(url_for("dashboard"))

# ---- Notify ----
def _fetch_emails_by_status_for_today(target, admin_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if target == "all":
        c.execute("SELECT email, guardian_email FROM students WHERE admin_id=?", (admin_id,))
    else:
        c.execute("""
            SELECT s.email, s.guardian_email
            FROM students s
            JOIN attendance a ON a.student_id = s.id
            WHERE a.admin_id = ? AND s.admin_id = ? AND a.date = ? AND a.status = ?
        """, (admin_id, admin_id, today, "Present" if target == "present" else "Absent"))

    rows = c.fetchall()
    conn.close()

    emails = []
    for r in rows:
        if r["email"]: emails.append(r["email"])
        if r["guardian_email"]: emails.append(r["guardian_email"])
    return list(dict.fromkeys(emails))

@app.route("/notify", methods=["POST"])
def notify():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    target = request.form.get("target")
    message_body = (request.form.get("message") or "").strip()

    if not message_body:
        return "Message body required", 400

    recipients = _fetch_emails_by_status_for_today(target, session["admin_id"])
    if not recipients:
        return "⚠ No recipients found."

    try:
        msg = Message("Attendance Notification", recipients=recipients)
        msg.body = message_body
        mail.send(msg)
        return "✅ Notification sent!"
    except Exception as e:
        print("Mail error:", e)
        return f"❌ Error sending mail: {str(e)}", 500

# ---- Run App ----
if __name__ == "__main__":
    app.run(debug=True)
