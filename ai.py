import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=api_key)


def analyze_resume(resume_text, user_goal):
    prompt = f"""
You are a senior software engineer and hiring manager.
Evaluate the resume based on the user's goal.

User goal: "{user_goal}"

STRICT RULES:
- Extract only relevant skills for this goal
- REMOVE irrelevant tools [Excel for backend, etc]
- Identify real gaps
- Generate roadmap only for missing fields
- Make output DIFFERENT based on different goals

Return only JSON:
{{
    "skills": [],
    "missing_skills": [],
    "roadmap": [],
    "interview_questions": []
}}

Resume:
{resume_text}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config={
                "temperature": 0.3,
                "response_mime_type": "application/json",
            },
        )

        content = response.text.strip()

        start = content.find("{")
        end = content.rfind("}") + 1

        return json.loads(content[start:end])

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": f"Invalid response format: {e}",
        }

    except Exception as e:
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": str(e),
        }