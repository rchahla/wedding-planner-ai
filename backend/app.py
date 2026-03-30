from flask import Flask, request, render_template, jsonify
from workflow import run_workflow

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
        "acknowledged": request.args.get("acknowledged", "false").lower() == "true"
    }

    result = run_workflow(user_input)

    has_conflicts = result.startswith("# Action Required")
    return jsonify({"report": result, "has_conflicts": has_conflicts})

if __name__ == "__main__":
    app.run(debug=True)
