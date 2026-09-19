import re
from flask import Flask, render_template, request, jsonify
from solver import solve_bathroom_bundle

app = Flask(__name__)

def parse_user_prompt_fallback(prompt_text):
    dims_match = re.search(r'(\d+)\s*(?:x|by|\*)\s*(\d+)', prompt_text, re.IGNORECASE)
    if dims_match:
        length = float(dims_match.group(2))
        width = float(dims_match.group(1))
    else:
        length, width = 10.0, 8.0

    budget_match = re.search(r'(?:\$|\bbudget\b|\bof\b)\s*(\d[\d,]+)', prompt_text, re.IGNORECASE)
    if budget_match:
        budget = float(budget_match.group(1).replace(',', ''))
    else:
        budget = 10000.0

    themes = ["Minimalist Modern", "Japanese Zen", "Classic Luxury"]
    selected_theme = "Minimalist Modern"
    for t in themes:
        if t.lower() in prompt_text.lower():
            selected_theme = t
            break

    return {
        "length_ft": length,
        "width_ft": width,
        "budget_usd": budget,
        "theme": selected_theme
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/design', methods=['POST'])
def generate_design():
    try:
        data = request.get_json() or {}
        user_prompt = data.get('prompt', '')
        parsed = parse_user_prompt_fallback(user_prompt)

        result = solve_bathroom_bundle(
            room_length_ft=parsed['length_ft'],
            room_width_ft=parsed['width_ft'],
            budget_usd=parsed['budget_usd'],
            theme=parsed['theme']
        )

        return jsonify({"status": "success", "data": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)