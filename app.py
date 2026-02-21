import os
import uuid
import fitz
import json
from flask import Flask, request, jsonify, render_template
from gtts import gTTS
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
AUDIO_FOLDER = "static/audio"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files["file"]

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF allowed"}), 400

    filename = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    try:
        # -------- Extract PDF Text --------
        doc = fitz.open(save_path)
        extracted_text = ""

        for i in range(min(3, len(doc))):
            extracted_text += doc.load_page(i).get_text()

        doc.close()

        clean_text = extracted_text.strip().replace("\n", " ")[:3000]

        # -------- Generate Summary --------
        summary_prompt = f"""
        Summarize the following academic content in 200 words.
        Focus on key learning concepts only.

        Content:
        {clean_text}
        """

        summary_response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=summary_prompt
        )

        summary = summary_response.text.strip()

        # -------- Generate Quiz --------
        quiz_prompt = f"""
        Create 3 multiple choice questions based on this summary.

        Rules:
        - Each question must have 4 options.
        - Provide correct answer clearly.
        - Return ONLY valid JSON.
        - Do NOT include explanation text.
        - Do NOT wrap in markdown.

        Format exactly like this:

        [
          {{
            "question": "Question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Correct option text"
          }}
        ]

        Summary:
        {summary}
        """

        quiz_response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=quiz_prompt
        )

        raw_quiz_text = quiz_response.text.strip()

        # -------- Robust JSON Cleaning --------
        if "```" in raw_quiz_text:
            raw_quiz_text = raw_quiz_text.replace("```json", "")
            raw_quiz_text = raw_quiz_text.replace("```", "")
            raw_quiz_text = raw_quiz_text.strip()

        # Extract only JSON array part
        start = raw_quiz_text.find("[")
        end = raw_quiz_text.rfind("]")

        if start != -1 and end != -1:
            raw_quiz_text = raw_quiz_text[start:end+1]

        try:
            quiz = json.loads(raw_quiz_text)
        except Exception as e:
            print("Quiz parsing failed:", e)
            print("Raw quiz text:", raw_quiz_text)
            quiz = []

        # -------- Generate Audio --------
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)

        tts = gTTS(summary)
        tts.save(audio_path)

        # -------- Return Final Response --------
        return jsonify({
            "success": True,
            "summary": summary,
            "audio_url": f"/static/audio/{audio_filename}",
            "quiz": quiz
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)