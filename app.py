"""Plumbline -- Flask entrypoint.

Request path for POST /api/design:

    free text -> ai_engine.parse_intent          Gemini, regex fallback
                        |
                        v
              solver.solve_bathroom_bundle       deterministic: cannot break
                        |                        budget or floor-area limits
                        v
          ai_engine.layout_with_fallback         Gemini proposes (wall, offset),
                        |                        layout.verify_layout critiques,
                        |                        Gemini repairs, solver backstops
                        v
                ai_engine.explain                rationale grounded on the
                                                 verified numbers only

The app starts and serves a valid design with no API key and no network.
"""
import os
import time

from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)

load_dotenv()

import ai_engine
from intent_parser import parse_prompt
from layout import mount_faucet
from solver import _fx, currency_of, load_catalog, solve_bathroom_bundle, water_use

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "plumbline-spatial-secret-key")

NAV = [("Planner", "planner"), ("Sustainability", "sustainability")]
THEMES = ["Minimalist Modern", "Japanese Zen", "Classic Luxury"]
LIMITS = {"length_ft": (4, 30), "width_ft": (4, 30), "household": (1, 12)}

# EPA WaterSense maximums -- the spec KOHLER certifies its products against.
WATERSENSE = {"toilet_gpf": 1.28, "shower_gpm": 2.0, "faucet_gpm": 1.5}


@app.context_processor
def inject_globals():
    return {"nav": NAV, "current": request.endpoint, "themes": THEMES,
            "ai_status": ai_engine.ai_status()}


@app.template_filter("format_number")
def format_number(value):
    return "{:,}".format(value)


# ------------------------------------------------------------------ pages --
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/planner")
def planner():
    return render_template("planner.html", currency=currency_of(load_catalog()))


@app.route("/sustainability", methods=["GET", "POST"])
def sustainability():
    occupancy = 4
    if request.method == "POST":
        try:
            occupancy = max(1, min(12, int(request.form.get("household_size", 4))))
        except (TypeError, ValueError):
            pass

    # Same water model as solver.py, so the two pages can never disagree.
    default_result = solve_bathroom_bundle(8, 8, 500000, household=occupancy)
    water_metrics = water_use(default_result["bundle"], occupancy)

    annual_gallons = water_metrics["saved_gal"]
    annual_rupees = int(annual_gallons * 3.78 * 0.05)

    return render_template("sustainability.html",
                           gallons_saved=annual_gallons,
                           rupees_saved=annual_rupees,
                           water_metrics=water_metrics,
                           ai_recommendation="WaterSense-certified selection")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", projects=session.get("projects", []))


@app.route("/auth")
def auth():
    return render_template("auth.html")


@app.route("/auth/login", methods=["POST"])
def login():
    session["user"] = "Architect User"
    return redirect(url_for("dashboard"))


@app.route("/api/health")
def health():
    """Lets a reviewer confirm in one request whether the LLM path is live."""
    return jsonify({"status": "ok", "gemini": ai_engine.ai_status(),
                    "model": ai_engine.MODEL, "catalog": len(load_catalog())})


@app.route("/api/health", methods=["GET"])
def health_check():
    import os
    import json
    with open("catalog.json", "r") as f:
        catalog = json.load(f)
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    return jsonify({
        "status": "ok",
        "gemini": "live" if api_key else "offline",
        "model": model,
        "catalog": len(catalog)
    })

@app.route("/api/projects/save", methods=["POST"])
def save_project():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    projects = session.get("projects", [])
    data["name"] = data.get("name", f"Project {len(projects) + 1}")
    projects.append(data)
    session["projects"] = projects
    return jsonify({"status": "success"})


# ----------------------------------------------------------- design API ----
def _validate(p):
    for key, (lo, hi) in LIMITS.items():
        if not lo <= p[key] <= hi:
            return f"{key.replace('_', ' ')} must be between {lo} and {hi}"
    if p["budget"] <= 0:
        return "budget must be greater than zero"
    if p["theme"] not in THEMES:
        return f"theme must be one of: {', '.join(THEMES)}"
    return None


def _watersense_report(bundle):
    """Per-product pass/fail against the EPA WaterSense spec KOHLER certifies to."""
    rows, passing = [], 0
    for p in bundle:
        cat = p["category"]
        if cat == "toilet":
            rated, limit, unit = p.get("gpf", 0), WATERSENSE["toilet_gpf"], "gpf"
        elif cat == "shower":
            rated, limit, unit = p.get("gpm", 0), WATERSENSE["shower_gpm"], "gpm"
        elif cat == "faucet":
            rated, limit, unit = p.get("gpm", 0), WATERSENSE["faucet_gpm"], "gpm"
        else:
            continue
        ok = rated <= limit + 1e-9
        passing += ok
        rows.append({"category": cat, "name": p["name"], "rated": rated,
                     "limit": limit, "unit": unit, "certified": ok})
    return {"items": rows, "certified_count": passing, "total": len(rows),
            "fully_certified": passing == len(rows) and bool(rows)}


@app.route("/api/design", methods=["POST"])
def generate_design():
    started = time.perf_counter()
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or ("prompt" not in body and "params" not in body):
        return jsonify({"status": "error",
                        "message": 'Send JSON with "prompt" or "params"'}), 400

    prompt_text = str(body.get("prompt", ""))
    try:
        if isinstance(body.get("params"), dict):
            raw = body["params"]
            parsed = {"length_ft": float(raw["length_ft"]),
                      "width_ft": float(raw["width_ft"]),
                      "budget": float(raw["budget"]), "theme": str(raw["theme"]),
                      "household": int(raw["household"]),
                      "prioritize_smart": bool(raw.get("prioritize_smart", False)),
                      "source": "controls", "assumed": [], "reading": None}
        else:
            # STEP 1 -- LLM reads intent, regex parser is the safety net.
            parsed = ai_engine.parse_intent(prompt_text, parse_prompt)
        parsed["prompt"] = prompt_text

        error = _validate(parsed)
        if error:
            return jsonify({"status": "error", "message": error}), 400

        # STEP 2 -- deterministic selection. Cannot exceed budget or floor limit.
        result = solve_bathroom_bundle(
            room_length_ft=parsed["length_ft"], room_width_ft=parsed["width_ft"],
            budget=parsed["budget"], theme=parsed["theme"],
            household=parsed["household"],
            prioritize_smart=parsed["prioritize_smart"])
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"status": "error", "message": f"Invalid request: {exc}"}), 400

    if result["status"] == "ok":
        W_in = result["layout"]["room_in"]["width"]
        L_in = result["layout"]["room_in"]["length"]
        by_cat = {p["category"]: p for p in result["bundle"]}
        floor = [_fx(p) for p in result["bundle"] if p["category"] != "faucet"]

        # STEP 3-6 -- propose, verify, repair, fall back. Always ends valid.
        placements, trace, source = ai_engine.layout_with_fallback(
            floor, W_in, L_in, parsed["theme"], prompt_text)

        if placements:
            for p in placements:
                item = by_cat[p["category"]]
                p.update(id=item["id"], name=item["name"])
            vanity = next(p for p in placements if p["category"] == "vanity")
            faucet = mount_faucet(_fx(by_cat["faucet"]), vanity, W_in, L_in)
            if faucet:
                faucet.update(id=by_cat["faucet"]["id"],
                              name=by_cat["faucet"]["name"])
                placements.append(faucet)
            result["layout"]["placements"] = placements

        result["ai"] = {
            "layout_source": source,
            "intent_source": parsed.get("source"),
            "reading": parsed.get("reading"),
            "attempts": len(trace),
            "repairs": sum(1 for t in trace if not t["accepted"]),
            "trace": trace,
            "status": ai_engine.ai_status(),
        }
        result["watersense"] = _watersense_report(result["bundle"])

        # STEP 7 -- narration grounded on the verified numbers.
        result["rationale"] = ai_engine.explain(result, prompt_text, parsed)

        # Flat aliases the existing front-end reads.
        result["room_dimensions_in"] = result["layout"]["room_in"]
        result["total_bundle_cost_inr"] = result["metrics"]["total_cost"]
        result["space_utilization_pct"] = result["metrics"]["space_utilization_pct"]
        result["annual_water_savings_gal"] = result["metrics"]["water"]["saved_gal"]
        result["budget_compliant"] = True

    return jsonify({"status": "success", "parsed": parsed, "data": result,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)})


if __name__ == "__main__":
    print(f"[plumbline] Gemini: {ai_engine.ai_status()} | model: {ai_engine.MODEL}")
    app.run(debug=True, port=5000)
