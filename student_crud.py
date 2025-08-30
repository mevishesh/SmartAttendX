from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

student_routes = Blueprint("students", __name__)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/database.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# === Route: Add New Student ===
@student_routes.route("/add_student", methods=["GET", "POST"])
def add_student():
    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        student_id = request.form["id"]
        name = request.form["name"]
        email = request.form["email"]

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO students (id, name, email, admin_id) VALUES (?, ?, ?, ?)",
                (student_id, name, email, session["admin_id"])
            )
            conn.commit()
            conn.close()
            flash("Student added successfully!", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Student ID already exists.", "error")
            return render_template("add_student.html")

    return render_template("add_student.html")
# === Route: Edit Student ===
@student_routes.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ? AND admin_id = ?",
        (student_id, session["admin_id"])
    ).fetchone()

    if not student:
        conn.close()
        flash("Student not found or unauthorized access.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        conn.execute(
            "UPDATE students SET name = ?, email = ? WHERE id = ?",
            (name, email, student_id)
        )
        conn.commit()
        conn.close()
        flash("Student updated successfully.", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("edit_student.html", student=student)


# === Route: Delete Student ===
@student_routes.route("/delete_student/<int:student_id>")
def delete_student(student_id):
    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM students WHERE id = ? AND admin_id = ?",
        (student_id, session["admin_id"])
    )
    conn.commit()
    conn.close()
    flash("Student deleted.", "success")
    return redirect(url_for("dashboard"))
