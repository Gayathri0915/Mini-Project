from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, get_flashed_messages
import sqlite3
import re
from datetime import datetime
import os   # ✅ ADDED

app = Flask(__name__)
app.secret_key = "gradeassure_secret_key"

DB_NAME = "database.db"


# -------------------- DATABASE CONNECTION --------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------- DATABASE SETUP --------------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marksheet_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_no TEXT NOT NULL,
            grade_sheet_no TEXT NOT NULL,
            month_year TEXT NOT NULL,
            status TEXT NOT NULL,
            issued_date TEXT,
            updated_date TEXT
        )
    """)

    # Ensure columns exist (for schema updates)
    try:
        cursor.execute("ALTER TABLE marksheet_data ADD COLUMN issued_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE marksheet_data ADD COLUMN updated_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


init_db()


# -------------------- HOME PAGE --------------------
@app.route("/")
def index():
    return render_template("index.html")


# -------------------- STUDENT SIDE --------------------
@app.route("/student")
def student_login():
    return render_template("student_login.html")


@app.route("/student_result", methods=["POST"])
def student_result():
    reg_no = request.form.get("reg_no").strip()

    if not re.match("^[0-9]{9}$", reg_no):
        return render_template("student_result.html", message="Register Number must be exactly 9 digits!")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT reg_no, grade_sheet_no, month_year, status, issued_date
        FROM marksheet_data
        WHERE reg_no = ?
        ORDER BY id DESC
    """, (reg_no,))

    all_data = cursor.fetchall()
    conn.close()

    if not all_data:
        return render_template("student_result.html", message="No Record Found")

    available_records = [row for row in all_data if row["status"].strip().lower() == "available"]

    if available_records:
        return render_template("student_result.html", all_data=all_data, not_issued=True, reg_no=reg_no)

    return render_template("student_result.html", all_data=all_data, issued=True, reg_no=reg_no)


@app.route("/download_form")
def download_form():
    return send_from_directory("static/files", "grade_not_issued_form.pdf", as_attachment=True)


# -------------------- FACULTY LOGIN --------------------
@app.route("/faculty")
def faculty_login():
    return render_template("faculty_login.html")


@app.route("/faculty_login", methods=["POST"])
def faculty_login_check():
    fid = request.form.get("fid").strip().upper()
    password = request.form.get("password").strip()

    if not re.match("^[A-Z][0-9]{4}$", fid):
        return render_template("faculty_login.html",
                               message="Faculty ID must be 1 CAPITAL letter + 4 digits (Example: A1234)",
                               msg_type="error")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM faculty WHERE faculty_id=?", (fid,))
    user = cursor.fetchone()

    if user is None:
        cursor.execute("INSERT INTO faculty (faculty_id, password) VALUES (?,?)", (fid, password))
        conn.commit()
        conn.close()

        return render_template("faculty_login.html",
                               message="Registered Successfully! Login again.",
                               msg_type="success")

    if user["password"] == password:
        conn.close()
        return redirect(url_for("faculty_dashboard"))

    conn.close()
    return render_template("faculty_login.html",
                           message="Invalid Password!",
                           msg_type="error")


# -------------------- FACULTY DASHBOARD --------------------
@app.route("/faculty_dashboard")
def faculty_dashboard():
    return render_template("faculty_dashboard.html")


@app.route("/logout")
def logout():
    return redirect(url_for("index"))


# -------------------- ENTRY MARKSHEET --------------------
@app.route("/enter_marksheet")
def enter_marksheet():
    get_flashed_messages()
    return render_template("enter_marksheet.html")


@app.route("/save_marksheet", methods=["POST"])
def save_marksheet():
    reg_no = request.form.get("reg_no")
    grade_sheet_no = request.form.get("grade_sheet_no").strip().upper()
    month_year = request.form.get("month_year")
    status = request.form.get("status")

    if not re.match("^[0-9]{9}$", reg_no):
        flash("Register Number must be exactly 9 digits!", "error")
        return redirect(url_for("enter_marksheet"))

    if not re.match("^[A-Z][0-9]{6}$", grade_sheet_no):
        flash("Grade Sheet Number must be 1 CAPITAL letter + 6 digits (Example: A098760)", "error")
        return redirect(url_for("enter_marksheet"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM marksheet_data WHERE grade_sheet_no = ?", (grade_sheet_no,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        flash("Duplicate Grade Sheet Number!", "error")
        return redirect(url_for("enter_marksheet"))

    cursor.execute("""
        INSERT INTO marksheet_data (reg_no, grade_sheet_no, month_year, status)
        VALUES (?, ?, ?, ?)
    """, (reg_no, grade_sheet_no, month_year, status))

    conn.commit()

    cursor.execute("""
        SELECT reg_no, grade_sheet_no, month_year, status
        FROM marksheet_data
        ORDER BY id DESC
    """)
    all_data = cursor.fetchall()

    conn.close()

    flash("Saved Successfully!", "success")
    return render_template("marksheet_table.html", all_data=all_data)


# -------------------- RUN APP --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))   # ✅ IMPORTANT FOR RENDER
    app.run(host="0.0.0.0", port=port, debug=True)