import time

# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, redirect, render_template, request, url_for, session

from intent_parser import parse_prompt
from solver import load_catalog, currency_of, solve_bathroom_bundle

app = Flask(__name__)
app.secret_key = 'kohler-spatial-secret-key'

# Add a page here (and a route below) and it appears in the nav automatically.
NAV = [("Planner", "planner")]

THEMES = ["Minimalist Modern", "Japanese Zen", "Classic Luxury"]
LIMITS = {"length_ft": (4, 30), "width_ft": (4, 30), "household": (1, 12)}


@app.context_processor
def inject_globals():
    return {"nav": NAV, "current": request.endpoint, "themes": THEMES}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/planner")
def planner():
    return render_template("planner.html", currency=currency_of(load_catalog()))


@app.route("/sustainability")
def sustainability():
    return render_template("sustainability.html")


@app.route("/dashboard")
def dashboard():
    projects = session.get("projects", [])
    return render_template("dashboard.html", projects=projects)


@app.route("/auth")
def auth():
    return render_template("auth.html")


@app.route("/auth/login", methods=["POST"])
def login():
    session["user"] = "Architect User"
    return redirect(url_for("dashboard"))


@app.route("/api/projects/save", methods=["POST"])
def save_project():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    if "projects" not in session:
        session["projects"] = []
    
    projects = session["projects"]
    data["name"] = data.get("name", f"Project {len(projects) + 1}")
    projects.append(data)
    session["projects"] = projects
    return jsonify({"status": "success"})


def _validate(p):
    """Return an error string, or None if the parameters are usable."""
    for key, (lo, hi) in LIMITS.items():
        if not lo <= p[key] <= hi:
            return f"{key.replace('_', ' ')} must be between {lo} and {hi}"
    if p["budget"] <= 0:
        return "budget must be greater than zero"
    if p["theme"] not in THEMES:
        return f"theme must be one of: {', '.join(THEMES)}"
    return None


@app.route("/api/design", methods=["POST"])
def generate_design():
    started = time.perf_counter()
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or ("prompt" not in body and "params" not in body):
        return jsonify({"status": "error", "message": 'Send JSON with "prompt" or "params"'}), 400
    try:
        if isinstance(body.get("params"), dict):
            raw = body["params"]
            parsed = {"length_ft": float(raw["length_ft"]), "width_ft": float(raw["width_ft"]),
                      "budget": float(raw["budget"]), "theme": str(raw["theme"]),
                      "household": int(raw["household"]),
                      "prioritize_smart": bool(raw.get("prioritize_smart", False)),
                      "source": "controls", "assumed": []}
        else:
            parsed = parse_prompt(str(body.get("prompt", "")))

        error = _validate(parsed)
        if error:
            return jsonify({"status": "error", "message": error}), 400

        result = solve_bathroom_bundle(
            room_length_ft=parsed["length_ft"], room_width_ft=parsed["width_ft"],
            budget=parsed["budget"], theme=parsed["theme"], household=parsed["household"],
            prioritize_smart=parsed["prioritize_smart"])
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"status": "error", "message": f"Invalid request: {exc}"}), 400

    if result["status"] == "ok":
        result["room_dimensions_in"] = result["layout"]["room_in"]
        result["total_bundle_cost_inr"] = result["metrics"]["total_cost"]
        result["space_utilization_pct"] = result["metrics"]["space_utilization_pct"]
        result["annual_water_savings_gal"] = result["metrics"]["water"]["saved_gal"]
        result["budget_compliant"] = True

    return jsonify({"status": "success", "parsed": parsed, "data": result,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
