from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
import sqlite3
import os
import sys
import platform
import subprocess
from datetime import datetime
import shutil

from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "your-secret-key"

# ---------------- Mail configuration ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "smartattendx@gmail.com"        # sender Gmail
app.config['MAIL_PASSWORD'] = "xadq ichq urrr ponl"           # Gmail app password
app.config['MAIL_DEFAULT_SENDER'] = "smartattendx@gmail.com"

mail = Mail(app)

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "database.db")

STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- Database Helper ----------------
def init_db():
    """Ensure required tables exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Admins table (includes optional profile_pic path)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_pic TEXT
        )
    """)

    # Students table (includes guardian_email)
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

    # Attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT NOT NULL,         -- YYYY-MM-DD
            status TEXT NOT NULL,       -- 'Present' or 'Absent'
            admin_id INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(admin_id) REFERENCES admins(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

def is_logged_in():
    return "admin_id" in session

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---- Profile ----
@app.route("/profile")
def profile():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch current admin info
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
        # Save as static/uploads/profile_<id>.png
        filename = f"profile_{session['admin_id']}.png"
        save_path = os.path.join(UPLOAD_DIR, filename)
        profile_pic.save(save_path)
        # store as URL path relative to /static
        pic_rel_url = f"uploads/{filename}".replace("\\", "/")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if pic_rel_url:
        c.execute(
            "UPDATE admins SET name = ?, email = ?, profile_pic = ? WHERE id = ?",
            (name, email, pic_rel_url, session["admin_id"])
        )
    else:
        c.execute(
            "UPDATE admins SET name = ?, email = ? WHERE id = ?",
            (name, email, session["admin_id"])
        )
    conn.commit()
    conn.close()

    session["admin_name"] = name
    flash("Profile updated successfully.", "success")
    return redirect(url_for("profile"))

# ---- Auth ----
@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json(force=True)
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""

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

@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def api_register():
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

# ---- Dashboard ----
from datetime import datetime

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # All students for this admin
    c.execute("""
        SELECT id, student_id, name, roll_no, email, guardian_no, guardian_email
        FROM students
        WHERE admin_id = ?
    """, (session["admin_id"],))
    students = c.fetchall()

    today = datetime.now().strftime("%Y-%m-%d")

    # Get attendance stats for today
    c.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE date = ? AND status = 'Present' AND admin_id = ?
    """, (today, session["admin_id"]))
    present_count = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE date = ? AND status = 'Absent' AND admin_id = ?
    """, (today, session["admin_id"]))
    absent_count = c.fetchone()[0]

    # Attendance records (optional)
    attendance_records = c.execute(
        """
        SELECT a.id, a.student_id, s.name, s.roll_no, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.admin_id = ?
        ORDER BY a.date DESC
        """,
        (session["admin_id"],)
    ).fetchall()

    attendance_records = [dict(zip(
        ['id','student_id','name','roll_no','date','status'],
        row
    )) for row in attendance_records]

    # Fetch current admin info
    c.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],))
    admin = c.fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        admin=admin,
        present_count=present_count,
        absent_count=absent_count,
        total_students=students,
        datetime=datetime   # ✅ pass datetime object to template
    )


    # Today's attendance counts
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE date = ? AND status = 'Present' AND admin_id = ?
    """, (today, session["admin_id"]))
    present_count = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE date = ? AND status = 'Absent' AND admin_id = ?
    """, (today, session["admin_id"]))
    absent_count = c.fetchone()[0]

    # Query all attendance records, join with student info (NO a.time)
    attendance_records = c.execute(
        """
        SELECT a.id, a.student_id, s.name, s.roll_no, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.admin_id = ?
        ORDER BY a.date DESC
        """,
        (session["admin_id"],)
    ).fetchall()

    attendance_records = [dict(zip(
        ['id','student_id','name','roll_no','date','status'],
        row
    )) for row in attendance_records]

    # Fetch current admin info
    c.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],))
    admin = c.fetchone()

    conn.close()

    response = make_response(render_template(
        "dashboard.html",
        admin=admin,
        present_count=present_count,
        absent_count=absent_count,
        attendance_records=attendance_records,
        total_students=students
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ---- Attendance + Registration Scripts ----
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

@app.route("/register-student", methods=["POST"])
def register_student():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    # -------- Get form data --------
    student_id     = (request.form.get("student_id") or "").strip()
    name           = (request.form.get("name") or "").strip()
    email          = (request.form.get("email") or "").strip()
    roll_no        = (request.form.get("roll_no") or "").strip()
    guardian_no    = (request.form.get("guardian_no") or "").strip()
    guardian_email = (request.form.get("guardian_email") or "").strip()

    if not student_id or not name:
        flash("Student ID and Name are required", "warning")
        return redirect(url_for("dashboard"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # -------- Check for duplicate student_id --------
    c.execute("SELECT id FROM students WHERE student_id = ?", (student_id,))
    existing = c.fetchone()
    if existing:
        conn.close()
        flash(f"⚠ Student ID {student_id} already exists.", "warning")
        return redirect(url_for("dashboard"))

    # -------- Insert student into DB --------
    c.execute("""
        INSERT INTO students (student_id, name, email, roll_no, guardian_no, guardian_email, admin_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_id, name, email, roll_no, guardian_no, guardian_email, session["admin_id"]))
    conn.commit()
    conn.close()

    # -------- Launch register_user.py with student_id --------
    try:
        script_path = os.path.join(BASE_DIR, "face_recognition", "register_user.py")
        popen_kwargs = {}
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

        subprocess.Popen([
            sys.executable,
            script_path,
            student_id,  # <-- Use form student_id, NOT DB auto-increment
            name,
            roll_no,
            email,
            guardian_no,
            guardian_email
        ], **popen_kwargs)

        flash(f"✅ Student {name} added. Starting face capture…", "success")
    except Exception as e:
        print("[ERROR] Could not start register_user.py:", e)
        flash("Student added but could not start face capture script. Check server logs.", "danger")

    return redirect(url_for("dashboard"))


# ---- Notify ----
def _fetch_emails_by_status_for_today(target: str, admin_id: int):
    """
    Returns list of recipient emails (students + guardians) for today's Present/Absent/All.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if target == "all":
        c.execute("SELECT email, guardian_email FROM students WHERE admin_id = ?", (admin_id,))
        rows = c.fetchall()
    else:
        # Join students with attendance filtered by today and status
        c.execute("""
            SELECT s.email, s.guardian_email
            FROM students s
            JOIN attendance a ON a.student_id = s.id
            WHERE a.admin_id = ?
              AND s.admin_id = ?
              AND a.date = ?
              AND a.status = ?
        """, (admin_id, admin_id, today, "Present" if target == "present" else "Absent"))
        rows = c.fetchall()

    conn.close()

    recipients = []
    for r in rows:
        if r["email"]:
            recipients.append(r["email"])
        if r["guardian_email"]:
            recipients.append(r["guardian_email"])
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for x in recipients:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique

@app.route("/notify", methods=["POST"])
def notify():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    target = request.form.get("target")  # "all" | "present" | "absent"
    message_body = (request.form.get("message") or "").strip()

    if target not in {"all", "present", "absent"}:
        return "Invalid target", 400
    if not message_body:
        return "Message body is required.", 400

    recipients = _fetch_emails_by_status_for_today(target, session["admin_id"])

    if not recipients:
        return "⚠ No recipients found."

    try:
        msg = Message("Attendance Notification", recipients=recipients)
        msg.body = message_body
        mail.send(msg)
        return "✅ Notification sent successfully!"
    except Exception as e:
        print("Mail error:", e)
        return f"❌ Error sending mail: {str(e)}", 500

# ---- Attendance History ----
@app.route("/attendance-history/<int:student_id>")
def attendance_history(student_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # student info
    c.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = c.fetchone()
    if not student:
        conn.close()
        return "Student not found", 404

    # attendance WITHOUT admin filter (for testing)
    c.execute(
        "SELECT date, status FROM attendance WHERE student_id = ? ORDER BY date DESC",
        (student_id,)
    )
    records = c.fetchall()
    conn.close()

    return render_template("attendance_history.html", student=student, records=records)

@app.route("/reset-data", methods=["POST"])
def reset_data():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    choice = request.form.get("reset_choice")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "database.db")
    TRAINED_DIR = os.path.join(BASE_DIR, "face_recognition", "trained_faces")

    conn = None
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)

    msg = ""
    try:
        if choice == "1":
            if conn:
                conn.execute("DELETE FROM attendance;")
                conn.commit()
                msg = "All attendance history cleared."
        elif choice == "2":
            if conn:
                conn.execute("DELETE FROM students;")
                conn.execute("DELETE FROM attendance;")
                conn.commit()
                msg = "All students & their attendance cleared."
        elif choice == "3":
            if conn:
                conn.execute("DELETE FROM admins;")
                conn.execute("DELETE FROM students;")
                conn.execute("DELETE FROM attendance;")
                conn.commit()
                msg = "All admins, students & attendance cleared."
        elif choice == "4":
            if os.path.exists(TRAINED_DIR):
                shutil.rmtree(TRAINED_DIR)
                msg = f"Trained faces folder removed."
            else:
                msg = "No trained faces folder found."
        elif choice == "5":
            if os.path.exists(DB_PATH):
                if conn:
                    conn.close()
                os.remove(DB_PATH)
                msg = "Database removed."
            if os.path.exists(TRAINED_DIR):
                shutil.rmtree(TRAINED_DIR)
                msg += " Trained faces folder removed."
            msg += " Everything wiped."
        else:
            msg = "Invalid choice."
    except Exception as e:
        msg = f"Error: {str(e)}"
    finally:
        if conn:
            conn.close()

    flash(msg, "info")
    return redirect(url_for("dashboard"))

#date  picker 

@app.route("/get-attendance/<date>")
def get_attendance(date):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT 
            s.name, 
            s.roll_no, 
            COALESCE(a.status, 'Absent') AS status
        FROM students s
        LEFT JOIN attendance a 
            ON s.id = a.student_id 
            AND a.date = ?
        WHERE s.admin_id = ?
        ORDER BY s.roll_no
    """, (date, session["admin_id"]))
    
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

#total students

@app.route("/student-history/<int:student_id>/<year>/<month>")
def student_history_month(student_id, year, month):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get attendance counts for that month
    c.execute("""
        SELECT status, COUNT(*) as count
        FROM attendance
        WHERE student_id = ? AND admin_id = ?
          AND strftime('%Y', date) = ? 
          AND strftime('%m', date) = ?
        GROUP BY status
    """, (student_id, session["admin_id"], str(year), str(month).zfill(2)))

    data = {"Present": 0, "Absent": 0}
    for row in c.fetchall():
        data[row["status"]] = row["count"]

    conn.close()
    return jsonify(data)



# ---------------- Main ----------------
if __name__ == "__main__":
    # Make sure Flask-Mail is installed:
    #   pip install Flask-Mail
    app.run(debug=True)
