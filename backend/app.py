from flask import Flask, request
from workflow import run_workflow

app = Flask(__name__)

@app.route("/")
def home():
    return "Wedding Planner AI is running!"

@app.route("/plan")
def plan():
    # Get inputs from URL
    guest_count = int(request.args.get("guests", 0))
    budget = int(request.args.get("budget", 0))

    user_input = {
        "guest_count": guest_count,
        "budget": budget
    }

    result = run_workflow(user_input)
    return result

if __name__ == "__main__":
    app.run(debug=True)