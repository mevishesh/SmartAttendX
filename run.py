from flask import Flask, render_template, request, redirect, url_for, session
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


# ✅ Home route (login page)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['name']
            return redirect(url_for('dashboard'))
        else:
            return "❌ Invalid credentials"
    return render_template('login.html')


# ✅ Dashboard with chart and student list
@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get student list
    c.execute("SELECT * FROM students WHERE admin_id = ?", (session['admin_id'],))
    students = c.fetchall()

    # Attendance chart counts
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND admin_id = ?", (today, session['admin_id']))
    present_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM students WHERE admin_id = ?", (session['admin_id'],))
    total_students = c.fetchone()[0]
    absent_count = total_students - present_count

    conn.close()

    return render_template('dashboard.html',
                           students=students,
                           admin_name=session['admin_name'],
                           present_count=present_count,
                           absent_count=absent_count)


# ✅ Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ✅ Start face-based attendance (calls recognizer.py)
@app.route('/start-attendance', methods=['POST'])
def start_attendance():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    subprocess.Popen(['python', 'face_recognition/recognizer.py'])
    return redirect(url_for('dashboard'))


# ✅ Add Student (Form)
@app.route('/add-student', methods=['GET'])
def add_student_form():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('add_student.html')


# ✅ Add Student (Submit)
@app.route('/add-student', methods=['POST'])
def add_student():
    if not is_logged_in():
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO students (name, email, admin_id) VALUES (?, ?, ?)", (name, email, session['admin_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


# ✅ Edit Student Form
@app.route('/edit-student/<int:id>', methods=['GET'])
def edit_student(id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id = ?", (id,))
    student = c.fetchone()
    conn.close()
    return render_template('edit_student.html', student=student)


# ✅ Update Student
@app.route('/edit-student/<int:id>', methods=['POST'])
def update_student(id):
    if not is_logged_in():
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE students SET name = ?, email = ? WHERE id = ?", (name, email, id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


# ✅ Delete Student
@app.route('/delete-student/<int:id>', methods=['POST'])
def delete_student(id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


# ✅ Notify absent students via email
@app.route('/notify', methods=['POST'])
def notify_absent():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    subprocess.Popen(['python', 'email_notifier.py'])
    return redirect(url_for('dashboard'))


# ✅ Run app
if __name__ == '__main__':
    app.run(debug=True)
