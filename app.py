import time
import pickle
import pandas as pd

# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, redirect, render_template, request, url_for, session

import os
import json
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "DUMMY_KEY"))

from intent_parser import parse_prompt
from solver import load_catalog, currency_of, solve_bathroom_bundle, clamp_coordinates
from layout import verify_layout

app = Flask(__name__)
app.secret_key = 'kohler-spatial-secret-key'

# Load Random Forest Model
try:
    with open('kohler_tier_model.pkl', 'rb') as f:
        rf_model = pickle.load(f)
except Exception as e:
    print(f"Warning: Model not loaded: {e}")
    rf_model = None

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


@app.template_filter('format_number')
def format_number(value):
    return "{:,}".format(value)

@app.route('/sustainability', methods=['GET', 'POST'])
def sustainability():
    # 1. Fallback Defaults
    budget_inr = 600000
    sqft = 80
    occupancy = 4
    eco_priority = 3

    # 2. Process Frontend Sidebar Inputs
    if request.method == 'POST':
        try:
            budget_inr = float(request.form.get('budget', 600000))
            length = float(request.form.get('length', 10))
            width = float(request.form.get('width', 8))
            sqft = length * width
            occupancy = int(request.form.get('household_size', 4))
            
            # Map the checkbox to maximum eco-priority
            if request.form.get('smart_features'):
                eco_priority = 5
            else:
                eco_priority = 3
        except ValueError:
            pass # Use defaults if form data is corrupt

    # Calculate Savings for UI
    toilet_savings_per_use = 3.50 - 1.28
    flushes_per_person_per_day = 5
    daily_savings = toilet_savings_per_use * flushes_per_person_per_day * occupancy
    annual_gallons_saved = int(daily_savings * 365)
    annual_liters_saved = annual_gallons_saved * 3.78
    annual_rupees_saved = int(annual_liters_saved * 0.05)

    # 3. Model Inference (Native INR)
    predicted_tier_name = "Kohler Eco-Smart Collection"
    
    if rf_model is not None: # Using the loaded 'kohler_tier_model.pkl'
        prediction = rf_model.predict([[budget_inr, sqft, occupancy, eco_priority]])[0]
        if prediction == 0:
            predicted_tier_name = "Kohler Standard Line"
        elif prediction == 1:
            predicted_tier_name = "Kohler Eco-Smart Collection"
        else:
            predicted_tier_name = "Kohler Luxury Numi Series"

    return render_template('sustainability.html', 
                           gallons_saved=annual_gallons_saved,
                           rupees_saved=annual_rupees_saved,
                           ai_recommendation=predicted_tier_name)


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
            parsed["prompt"] = str(body.get("prompt", ""))

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

        # Call Gemini for Dynamic Layout Generation
        W_in = result["layout"]["room_in"]["width"]
        L_in = result["layout"]["room_in"]["length"]
        
        prompt_text = f"""
        You are an AI layout generator for a bathroom.
        Room dimensions: width {W_in} inches, length {L_in} inches.
        Theme: {parsed["theme"]}
        User request: {parsed.get("prompt", "")}
        
        You must place the following fixtures. For each fixture, provide its x and y coordinates (in inches) from the top-left corner (0,0).
        Rules:
        1. No fixture can exceed the room boundaries: x + w + 15 <= {W_in} and y + d + 15 <= {L_in}. (15 inches is the standard clearance).
        2. Fixtures cannot overlap each other's clearance zones.
        3. Faucets should be placed on the vanity.
        
        Fixtures:
        """
        for p in result["layout"]["placements"]:
            prompt_text += f"- {p['category']} (w: {p.get('w', 0)}, d: {p.get('d', 0)})\n"
            
        prompt_text += """
        Return STRICT JSON format only, exactly like this example, with no markdown formatting or extra text:
        {"shower": {"x": 0, "y": 0, "w": 36, "d": 36}, "toilet": {"x": 40, "y": 0, "w": 20, "d": 28}, "vanity": {"x": 80, "y": 40, "w": 30, "d": 22}, "faucet": {"x": 85, "y": 40, "w": 5, "d": 5}}
        """
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt_text)
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:-3].strip()
            elif text.startswith('```'):
                text = text[3:-3].strip()
            gemini_coords = json.loads(text)
            
            # 1. Update the placements with raw Gemini coordinates
            for p in result["layout"]["placements"]:
                cat = p["category"]
                if cat in gemini_coords:
                    p["original_x"] = p.get("x", 0)
                    p["original_y"] = p.get("y", 0)
                    p["x"] = float(gemini_coords[cat].get("x", p["original_x"]))
                    p["y"] = float(gemini_coords[cat].get("y", p["original_y"]))
                    
            # 2. Enforce physical constraints via solver
            result["layout"]["placements"] = clamp_coordinates(result["layout"]["placements"], W_in, L_in)
            
            # 3. Re-verify the layout with the new coordinates to update IBC Code checks
            new_problems = verify_layout(result["layout"]["placements"], W_in, L_in)
            for chk in result["checks"]:
                if chk["name"] == "Clearances":
                    chk["passed"] = not any("clearance" in x for x in new_problems)
                elif chk["name"] == "Door swing":
                    chk["passed"] = not any("door" in x for x in new_problems)
                elif chk["name"] == "No overlaps":
                    chk["passed"] = not any("overlaps" in x or "outside" in x for x in new_problems)
                    
        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback to deterministic layout if Gemini fails

    return jsonify({"status": "success", "parsed": parsed, "data": result,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
