from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Blueprint setup
auth = Blueprint("auth", __name__)

# Database path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/database.db"))

# === Function to get DB connection ===
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # for dictionary-style rows
    return conn

# === Route: Register New Admin ===
@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Hash the password using Werkzeug
        hashed_pw = generate_password_hash(password)

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO admins (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_pw)
            )
            conn.commit()
            conn.close()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except sqlite3.IntegrityError:
            flash("Email already registered. Try logging in.", "error")
            return render_template("register.html")

    return render_template("register.html")

# === Route: Admin Login ===
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE email = ?", (email,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            # Login successful: save session
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")
            return render_template("login.html")

    return render_template("login.html")

# === Route: Logout ===
@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
