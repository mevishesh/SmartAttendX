from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import subprocess
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Define database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'database.db')


# ✅ Helper function to check admin session
def is_logged_in():
    return 'admin_id' in session


# ✅ API Login (used by login.html fetch)
@app.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password))
    admin = c.fetchone()
    conn.close()

    if admin:
        session['admin_id'] = admin['id']
        session['admin_name'] = admin['name']
        return jsonify({"success": "Login successful"})
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# ✅ API Register (used by register.html fetch)

@app.route('/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)  # ✅ ensure table exists

        c.execute("INSERT INTO admins (name, email, password) VALUES (?, ?, ?)",
                  (name, email, password))
        conn.commit()
        conn.close()

        return jsonify({"success": "Account created successfully!"})

    except Exception as e:
        print("❌ Registration error:", str(e))  # log in backend console
        return jsonify({"error": "Registration failed: " + str(e)})


# ✅ Serve login page (GET)
@app.route('/login-page', methods=['GET'])
def login_page():
    return render_template('login.html')


# ✅ Serve register page (GET)
@app.route('/register-page', methods=['GET'])
def register_page():
    return render_template('register.html')


# ✅ Landing page
@app.route('/')
def home():
    return render_template('index.html')


# ✅ Dashboard with chart and student list
@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login_page'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ✅ Get all students (no admin filter)
    c.execute("SELECT * FROM students")
    students = c.fetchall()

    # ✅ Attendance stats
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
    present_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]
    absent_count = total_students - present_count

    conn.close()

    return render_template(
        'dashboard.html',
        students=students,
        admin_name=session.get('admin_name', 'Admin'),
        present_count=present_count,
        absent_count=absent_count
    )


# ✅ Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ✅ Start face-based attendance
@app.route('/start-attendance', methods=['POST'])
def start_attendance():
    if not is_logged_in():
        return redirect(url_for('login_page'))

    subprocess.Popen(['python', 'face_recognition/recognizer.py'])
    return redirect(url_for('dashboard'))


# ✅ Run app
if __name__ == '__main__':
    app.run(debug=True)
