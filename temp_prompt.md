<USER_REQUEST>
Correctness and compliance fix. Every number in a template must trace to a JSON path in the /api/design response. If you cannot name the path, delete the element — do not reword it.

A. Delete fabricated data

sustainability.html: delete the pH / contaminants / VOC / "Tracking Live" card, the TEMP-K / NEXT SHIFT card, and the VAGAL TONE / HRV / NEURAL STATE card entirely. Delete all SOURCE: and NODE: tags. No sensor exists.
Delete every "IBC 2026 Code 405.3.1" and any other code-section citation, including the "IBC 2026 CODE VERIFICATION" heading in planner.html and "IBC CLEARANCE PASS". Replace with "Clearance verification" and the actual inch values from layout.py.
Delete "LEED COMPLIANCE TARGET" — replace with the real count from data.watersense.certified_count / .total.
Delete "✓ SPATIAL MATH VERIFIED" unless bound to data.checks.
dashboard.html: delete the hardcoded "8x10 Luxury Master Bath (Sample)" card.
Products page: delete "Access all 1,200+ … fixtures" — the catalogue has 16.
Landing: the CAD mockup is decorative and hardcoded. Either delete it or label it "Illustrative". Its "32" CLEAR SWING" contradicts DOOR_WIDTH_IN = 30.0.

B. Fix the water figures
8. /sustainability currently uses a toilet-only formula and shows 16,205 gal / 43.8%. The solver's water_use() models toilet + shower + faucet and returns 27,886 gal / 45.6% for household 4. Import water_use from solver.py and use it. The chart bars must come from that same function, not hardcoded values. Both pages must show identical numbers for identical inputs.

C. Brand scrub — remaining hits
9. Landing: "The Kohler Spatial Solver" → "The Plumbline spatial solver". "16-item Kohler India catalog" → "16-item product catalogue". Fix the garbled badge "Plumbline & PLANNER" → "PLUMBLINE PLANNER".
10. Products: "OFFICIAL KOHLER INDIA CATALOG" → "PRODUCT CATALOGUE". Delete the "VIEW FULL KOHLER INDIA CATALOG ON KOHLER.CO.IN" button entirely.
11. Sustainability: "Standard Baseline vs Kohler Eco-Smart" → "Legacy baseline vs WaterSense-certified selection". "Kohler's 1.2 GPM aerators" → "1.2 GPM aerators".
12. Planner: "CURATED KOHLER FINISHES" → "AVAILABLE FINISHES". "OFFICIAL KOHLER INDIA SPECIFICATION" → "FIXTURE SCHEDULE".
13. Footer on every page: remove the KOHLER wordmark and the copyright line. Replace with: "Plumbline — independent student prototype. Not affiliated with or endorsed by any manufacturer."
14. Fix "Optimized Tier: Plumbline WaterSense-certified selection" — a find/replace artifact. Should read "WaterSense-certified selection".

D. Favicon and wordmark
15. Replace the browser-tab favicon (currently a "K"). Create static/favicon.svg containing a plumb-bob mark: a vertical line from the top with a small triangle/teardrop weight at the bottom, in currentColor on transparent. Link it in base.html with <link rel="icon" href="{{ url_for('static', filename='favicon.svg') }}">. Delete any existing favicon.ico or K-based icon file.

Then run python -m pytest tests/ -q — 22 must pass — and report which files changed.

One thing that's still missing entirely

There's no AI reasoning panel on the planner. That's Phase 2, and it's your 45%. Also: SOLVED IN 1472.9 ms at ~1.5 seconds means Gemini was being called and retried — but with gemini-2.5-flash 404ing, every one of those layouts came from the deterministic fallback.

Set GEMINI_MODEL=gemini-3.6-flash in .env before anything else. Until that's fixed, you have no AI running at all, and the panel would have nothing to show
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-09-21T23:00:00+05:30.

The user's current state is as follows:
Active Document: c:\Users\DELL\Desktop\kohler\app.py (LANGUAGE_PYTHON)
Cursor is on line: 240
Other open documents:
- c:\Users\DELL\Desktop\kohler\templates\base.html (LANGUAGE_HTML)
- c:\Users\DELL\Desktop\kohler\.gitignore (LANGUAGE_UNSPECIFIED)
- c:\Users\DELL\Desktop\kohler\.env (LANGUAGE_UNSPECIFIED)
- c:\Users\DELL\Desktop\kohler\static\js\planner.js (LANGUAGE_JAVASCRIPT)
- c:\Users\DELL\Desktop\kohler\templates\planner.html (LANGUAGE_HTML)
Running terminal commands:
- python app.py (in c:\Users\DELL\Desktop\kohler, running for 8m54s)
</ADDITIONAL_METADATA>
<USER_SETTINGS_CHANGE>
The user changed setting `Model Selection` from None to Gemini 3.1 Pro (High). No need to comment on this change if the user doesn't ask about it. If reporting what model you are, please use a human readable name instead of the exact string.
</USER_SETTINGS_CHANGE>