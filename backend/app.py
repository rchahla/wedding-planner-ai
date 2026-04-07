import os
from flask import Flask, request, render_template, jsonify
from workflow import run_workflow
from state import load_state
from artifact_generator import generate_with_gemini, OUTPUT_FILE

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/plan")
def plan():
    user_input = {
        "guest_count": int(request.args.get("guests", 0)),
        "budget":      int(request.args.get("budget", 0)),
        "theme":       request.args.get("theme", ""),
        "date":        request.args.get("date", ""),
        "venue_type":  request.args.get("venue_type", ""),
        "dietary":     request.args.get("dietary", ""),
        "email":       request.args.get("email", ""),
        "acknowledged": request.args.get("acknowledged", "false").lower() == "true"
    }

    result, emailed = run_workflow(user_input)

    has_conflicts = result.startswith("# Action Required")
    return jsonify({"report": result, "has_conflicts": has_conflicts, "emailed": emailed})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    state = load_state()

    report_content = ""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            report_content = f.read()

    prompt = f"""You are a helpful wedding planning assistant. The couple has already received a planning report. Answer their follow-up question concisely and specifically, referencing their actual event details where relevant.

## Their Event Details
- Guest Count: {state.get("guest_count", "Not provided")}
- Budget: ${state.get("budget", "Not provided")}
- Theme: {state.get("theme", "Not provided")}
- Event Date: {state.get("date", "Not provided")}
- Venue Type: {state.get("venue_type", "Not provided")}
- Dietary Requirements: {state.get("dietary", "Not provided")}

## Their Planning Report
{report_content}

## Follow-up Question
{message}

Answer in 2–4 sentences unless a longer answer is clearly needed. Be specific — use their actual numbers and details."""

    response = generate_with_gemini(prompt)
    if not response or response.startswith("Error"):
        return jsonify({"error": "Could not generate a response. Please try again."}), 500

    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(debug=True)
