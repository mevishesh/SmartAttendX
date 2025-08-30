import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

# 📌 DB Location
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "database/database.db"))

# 🕒 Today's date
today = datetime.now().strftime("%Y-%m-%d")

# ✉️ Email configuration (change this to real sender credentials)
EMAIL_ADDRESS = "visheshwaghmore01@example.com"
EMAIL_PASSWORD = "tunn rzrk dhmv xksi"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# 📤 Send email function
def send_email(to_email, student_name):
    subject = f"[SecureAttendX] Absence Notification - {today}"
    body = f"Dear Parent,\n\nYour child {student_name} was marked absent today ({today}).\n\nPlease ensure regular attendance.\n\nThank you,\nSecureAttendX System"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"✅ Notification sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send to {to_email}: {e}")

# 🚀 Notify all absent students
def notify_absent_students():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all students
    students = c.execute("SELECT id, name, email FROM students").fetchall()

    for student in students:
        student_id = student["id"]
        name = student["name"]
        email = student["email"]

        # Check if attendance is marked for today
        attendance = c.execute(
            "SELECT * FROM attendance WHERE student_id = ? AND date = ?",
            (student_id, today)
        ).fetchone()

        if attendance is None:
            send_email(email, name)

    conn.close()

if __name__ == "__main__":
    notify_absent_students()
