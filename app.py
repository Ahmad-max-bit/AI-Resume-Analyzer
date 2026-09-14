import json

try:
    import docx  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency for .docx parsing
    docx = None

try:
    from flask import (  # type: ignore[import-not-found]
        Flask,
        redirect,
        render_template,
        request,
        session,
    )
except ImportError as exc:
    raise RuntimeError("Flask is required. Install dependencies with: pip install flask") from exc

try:
    from pypdf import PdfReader  # type: ignore[import-not-found]
except ImportError:
    from PyPDF2 import PdfReader  # type: ignore[import-not-found]

import models
from ai import analyze_resume
from db import Base, SessionLocal, engine

app = Flask(__name__)
app.secret_key = "secret123"

with app.app_context():
    Base.metadata.create_all(bind=engine)


@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


# SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    db = SessionLocal()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        existing_user = (
            db.query(models.User).filter_by(password=password, email=email).first()
        )
        if existing_user:
            return "User already exist"
        user = models.User(password=password, email=email)
        db.add(user)
        db.commit()
        print("USER SAVED:", email)
        print("USER ID:", user.id)
        return redirect("/login")
    return render_template("signup.html")


# login
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
        else:
            return "Invalid Credentials"

    return render_template("login.html")


# Dashboard
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")
    result = None
    if request.method == "POST":
        user_goal = request.form.get("role")
        resume_text = request.form.get("resume")
        file = request.files.get("file")


        # file handling
        if file and file.filename != "":
            if file.filename.endswith(".pdf"):
                try:
                    pdf_reader = PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                    resume_text = text
                except (AttributeError, OSError, ValueError, TypeError) as e:
                    result = {"error": f"PDF error: {e}"}

            elif file.filename.endswith(".docx"):
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

                # save to db
                db = SessionLocal()
                user = db.query(models.User).filter_by(email=session["user"]).first()
                report = models.Reports(
                    user_id=user.id, resume_text=resume_text, result=json.dumps(result)
                )

                db.add(report)
                db.commit()

            except (TypeError, ValueError, RuntimeError) as e:
                result = {"error": f"AI error: {e}"}
    return render_template("dashboard.html", user=session["user"], result=result)

# history
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()

    reports = db.query(models.Reports).filter_by(user_id=user.id).all()

    # convert to dict
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


# logout


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
