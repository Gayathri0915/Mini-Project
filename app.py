from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, get_flashed_messages
import sqlite3
import re
from datetime import datetime

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

    # Faculty Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT UNIQUE,
            password TEXT
        )
    """)

    # Marksheet Data Table
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


# ✅ UPDATED STUDENT RESULT FUNCTION (MULTIPLE RECORDS VIEW WITH CORRECT STATUS CHECK)
@app.route("/student_result", methods=["POST"])
def student_result():
    reg_no = request.form.get("reg_no").strip()

    # Validation: Must be 9 digits
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

    # If no record found
    if not all_data:
        return render_template("student_result.html", message="No Record Found")

    # ✅ CHECK IF ANY RECORD IS AVAILABLE (Not Issued)
    available_records = [row for row in all_data if row["status"].strip().lower() == "available"]

    # If any record is Available -> show download form option
    if available_records:
        return render_template("student_result.html", all_data=all_data, not_issued=True, reg_no=reg_no)

    # If all are Not Available -> already issued
    return render_template("student_result.html", all_data=all_data, issued=True, reg_no=reg_no)


# Download PDF form
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

    # Faculty ID Validation: 1 Capital + 4 digits
    if not re.match("^[A-Z][0-9]{4}$", fid):
        return render_template(
            "faculty_login.html",
            message="Faculty ID must be 1 CAPITAL letter + 4 digits (Example: A1234)",
            msg_type="error"
        )

    conn = get_db()
    cursor = conn.cursor()

    # Check if faculty exists
    cursor.execute("SELECT * FROM faculty WHERE faculty_id=?", (fid,))
    user = cursor.fetchone()

    # If faculty not exists -> register automatically
    if user is None:
        cursor.execute("INSERT INTO faculty (faculty_id, password) VALUES (?,?)", (fid, password))
        conn.commit()
        conn.close()

        return render_template(
            "faculty_login.html",
            message="Registered Successfully! Login again.",
            msg_type="success"
        )

    # If password correct -> login success
    if user["password"] == password:
        conn.close()
        return redirect(url_for("faculty_dashboard"))

    conn.close()
    return render_template(
        "faculty_login.html",
        message="Invalid Password!",
        msg_type="error"
    )


# -------------------- FACULTY DASHBOARD --------------------
@app.route("/faculty_dashboard")
def faculty_dashboard():
    return render_template("faculty_dashboard.html")


# -------------------- ENTRY MARKSHEET --------------------
@app.route("/enter_marksheet")
def enter_marksheet():
    get_flashed_messages()  # clears old flash messages (Fix)
    return render_template("enter_marksheet.html")


@app.route("/save_marksheet", methods=["POST"])
def save_marksheet():
    reg_no = request.form.get("reg_no")
    grade_sheet_no = request.form.get("grade_sheet_no").strip().upper()
    month_year = request.form.get("month_year")
    status = request.form.get("status")

    # Validation: reg_no must be 9 digits
    if not re.match("^[0-9]{9}$", reg_no):
        flash("Register Number must be exactly 9 digits!", "error")
        return redirect(url_for("enter_marksheet"))

    # Validation: grade_sheet_no pattern (Example: A098760)
    if not re.match("^[A-Z][0-9]{6}$", grade_sheet_no):
        flash("Grade Sheet Number must be 1 CAPITAL letter + 6 digits (Example: A098760)", "error")
        return redirect(url_for("enter_marksheet"))

    conn = get_db()
    cursor = conn.cursor()

    # -------------------- DUPLICATE CHECK --------------------
    cursor.execute("SELECT * FROM marksheet_data WHERE grade_sheet_no = ?", (grade_sheet_no,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        flash("Duplicate Grade Sheet Number! This Grade Sheet No already exists.", "error")
        return redirect(url_for("enter_marksheet"))

    # Insert data
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

    flash("Marksheet Data Saved Successfully!", "success")
    return render_template("marksheet_table.html", all_data=all_data)


# -------------------- UPDATE MARKSHEET --------------------
@app.route("/update_select")
def update_select():
    return render_template("update_select.html")


@app.route("/update_marksheet", methods=["POST"])
def update_marksheet():
    reg_no = request.form.get("reg_no")
    grade_sheet_no = request.form.get("grade_sheet_no").strip().upper()
    issued_date = request.form.get("issued_date")
    month_year = request.form.get("month_year")
    status = request.form.get("status")

    updated_date = datetime.now().strftime("%d-%m-%Y")

    # Validation: reg_no must be 9 digits
    if not re.match("^[0-9]{9}$", reg_no):
        flash("Register Number must be exactly 9 digits!", "error")
        return redirect(url_for("update_select"))

    # Validation: grade_sheet_no format
    if not re.match("^[A-Z][0-9]{6}$", grade_sheet_no):
        flash("Grade Sheet Number must be 1 CAPITAL letter + 6 digits (Example: A098760)", "error")
        return redirect(url_for("update_select"))

    conn = get_db()
    cursor = conn.cursor()

    # Check record exists
    cursor.execute("""
        SELECT * FROM marksheet_data
        WHERE reg_no = ? AND grade_sheet_no = ?
    """, (reg_no, grade_sheet_no))

    record = cursor.fetchone()

    if not record:
        conn.close()
        flash("Record not found! Please enter correct Register No and Grade Sheet No.", "error")
        return redirect(url_for("update_select"))

    # Update record
    cursor.execute("""
        UPDATE marksheet_data
        SET issued_date = ?, month_year = ?, status = ?, updated_date = ?
        WHERE reg_no = ? AND grade_sheet_no = ?
    """, (issued_date, month_year, status, updated_date, reg_no, grade_sheet_no))

    conn.commit()

    cursor.execute("""
        SELECT reg_no, grade_sheet_no, issued_date, month_year, status, updated_date
        FROM marksheet_data
        ORDER BY id DESC
    """)
    all_data = cursor.fetchall()

    conn.close()

    flash("Updated Successfully!", "success")
    return render_template("update_table.html", all_data=all_data)


# -------------------- VIEW DATA --------------------
@app.route("/view_select")
def view_select():
    return render_template("view_select.html")


# ✅ FIXED VIEW TABLE ROUTE (GET + POST)
@app.route("/view_table", methods=["GET", "POST"])
def view_table():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT reg_no, grade_sheet_no, issued_date, month_year, status, updated_date
        FROM marksheet_data
        ORDER BY id DESC
    """)
    all_data = cursor.fetchall()

    conn.close()

    return render_template("view_table.html", rows=all_data)


# -------------------- LOGOUT --------------------
@app.route("/logout")
def logout():
    return redirect(url_for("index"))


# -------------------- RUN APP --------------------
if __name__ == "__main__":
    app.run(debug=True)
