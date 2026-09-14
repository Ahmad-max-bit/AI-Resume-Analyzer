import json
import os

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from dotenv import load_dotenv
load_dotenv()

try:
    import docx  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency for .docx parsing
    docx = None

try:
    from pypdf import PdfReader  # type: ignore[import-not-found]
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - optional dependency for .pdf parsing
        PdfReader = None

import models
from ai import analyze_resume
from db import Base, SessionLocal, engine

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

with app.app_context():
    Base.metadata.create_all(bind=engine)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    db = SessionLocal()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        existing_user = db.query(models.User).filter_by(email=email).first()

        if existing_user:
            return "User already exist"

        user = models.User(password=password, email=email)
        db.add(user)
        db.commit()
        print("USER SAVED:", email)
        print("USER ID:", user.id)
        return redirect("/login")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    db = SessionLocal()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.query(models.User).filter_by(password=password, email=email).first()
        if user:
            session["user"] = user.email
            return redirect("/dashboard")
        return "Invalid Credentials"

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    result = None
    if request.method == "POST":
        user_goal = request.form.get("role")
        resume_text = request.form.get("resume")
        file = request.files.get("file")

        if file and file.filename != "":
            if file.filename.endswith(".pdf"):
                if PdfReader is None:
                    result = {"error": "PDF parsing library not installed."}
                else:
                    try:
                        pdf_reader = PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() or ""
                        resume_text = text
                    except (AttributeError, OSError, ValueError, TypeError) as e:
                        result = {"error": f"PDF error: {e}"}
            elif file.filename.endswith(".docx"):
                if docx is None:
                    result = {"error": "DOCX parsing library not installed."}
                else:
                    try:
                        doc = docx.Document(file)
                        text = ""
                        for para in doc.paragraphs:
                            text += para.text + "\n"
                        resume_text = text
                    except (AttributeError, OSError, ValueError, TypeError) as e:
                        result = {"error": f"Docx error: {e}"}

        if resume_text and user_goal:
            try:
                result = analyze_resume(resume_text, user_goal)
                db = SessionLocal()
                user = db.query(models.User).filter_by(email=session["user"]).first()
                report = models.Reports(
                    user_id=user.id,
                    resume_text=resume_text,
                    result=json.dumps(result),
                )
                db.add(report)
                db.commit()
            except (TypeError, ValueError, RuntimeError) as e:
                result = {"error": f"AI error: {e}"}

    return render_template("dashboard.html", user=session["user"], result=result)


@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()
    reports = db.query(models.Reports).filter_by(user_id=user.id).all()

    parsed_reports = []
    for r in reports:
        try:
            parsed_result = json.loads(r.result)
        except (json.JSONDecodeError, TypeError, ValueError):
            parsed_result = []

        parsed_reports.append(
            {
                "resume": r.resume_text,
                "result": parsed_result,
            }
        )

    return render_template("history.html", reports=parsed_reports)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
