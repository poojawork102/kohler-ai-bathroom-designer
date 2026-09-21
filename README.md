# Plumbline

**Conversational bathroom design with verified spatial compliance**
AI Lab Case Study — Track 1: AI Bathroom Designer & Planner | MIT-WPU

---

**Video walkthrough:** https://youtu.be/OoWaedDzoKU
**Prompts documentation:** [`docs/Plumbline_promptlog.pdf`](docs/Plumbline_promptlog.pdf)
**Pitch deck:** [`docs/Plumbline_ppt.pdf`](docs/Plumbline_ppt.pdf)
**Product requirements:** [`docs/Plumbline_prd.pdf`](docs/Plumbline_prd.pdf)

---

## What it does

Plumbline turns a plain-English request — *"8×10 spa bathroom, family of 4, ₹6 lakh, touchless"* — into a costed, clearance-verified, WaterSense-certified floor plan in under 2 seconds.

The product is named after its verifier, not its generator. A plumb line designs nothing — it only tells you whether what was built is true. The language model proposes; deterministic geometry disposes.

---

## The architecture

The core problem: LLMs are excellent at reading intent and making aesthetic judgements, and unreliable at metric geometry. Ask a model for fixture coordinates and it will cheerfully overlap a toilet with a shower.

Plumbline's answer is a **constrained action space + verify–repair–fallback loop**:

| Stage | Owner | What happens |
|---|---|---|
| 1. Understand | Gemini | Free text → structured brief. Regex parser is the fallback. |
| 2. Select | Python | Enumerates all 256 catalogue bundles. Filters by budget and 40% floor-area limit. Cannot return an over-budget bundle. |
| 3. Arrange | Gemini | Proposes `(wall, offset)` per fixture — never raw x/y. Coordinates are derived in code. |
| 4. Verify | Python | `verify_layout()` re-checks clearances, door swing and overlaps independently. |
| 5. Repair | Gemini | Violations fed back as a critique. Model retries, forbidden from repeating the rejected arrangement. Max 2 repairs. |
| 6. Fall back | Python | Constraint search ships a guaranteed-valid layout. A user never sees a broken plan. |
| 7. Narrate | Gemini | Rationale written using only the verified numbers — cannot invent a saving figure. |

The self-correction trace is returned under `data.ai.trace` and rendered in the UI — you can watch the model fail, receive a machine critique, and fix itself.

---

## Quickstart

```bash
git clone https://github.com/poojawork102/plumbline.git
cd plumbline

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # add your Gemini key (optional)
python app.py                   # http://localhost:5000
```

Or use Make:

```bash
make install
make run
make test
```

**The app runs with no API key.** Every page works offline — the AI stages degrade gracefully, they never crash. Confirm at:

```
GET /api/health
→ {"status":"ok","gemini":"live","model":"gemini-3.6-flash","catalog":16}
```

---

## Tests

```bash
python -m pytest tests/ -q
```

- **22 passing** — 18 solver/layout + 4 AI loop
- The 4 AI-loop tests use a stubbed model — no API key or network needed
- Tests prove the repair loop catches invalid layouts before they reach the user

---

## Project structure

```
app.py              Flask routes + 7-stage design pipeline
ai_engine.py        Gemini calls, constrained generation, verify→repair loop
solver.py           Deterministic bundle selection (budget, water, theme)
layout.py           Geometry, clearance envelopes, independent verifier
intent_parser.py    Regex intent parser (offline fallback)
catalog.json        16 products with real SKUs, flow rates, clearances
templates/          Planner, sustainability dashboard, landing page, auth
static/             CSS, JS, SVG favicon
tests/              22 unit tests including stubbed-model AI loop tests
docs/               Pitch deck, PRD, prompts documentation (PDF)
```

---

## Sustainability

Every design is checked against EPA WaterSense limits — the same thresholds independently tested per product:

- Toilet ≤ 1.28 gpf
- Shower ≤ 2.0 gpm
- Lavatory faucet ≤ 1.5 gpm

Annual water saving is modelled per fixture class against a legacy 3.5 gpf / 2.5 gpm baseline, scaled by household size. A typical family-of-four design saves **~27,886 gallons per year**.

Water savings are modelled from published flow ratings and assumed usage patterns, not metered data. Assumptions are stated in `solver.py` and changeable in one place.

---

## Scalability

Each extension below is a loader or config change — the solver and verifier don't move:

| Extension | Where it plugs in | Why it's not a rewrite |
|---|---|---|
| Live product catalogue | `load_catalog()` → PIM/API | Solver is catalogue-agnostic |
| Regional plumbing codes | Constants in `layout.py` → code profile | Clearances are data, not logic (IS 1172 / IBC / ADA) |
| Multi-room / whole-home | `solve_bathroom_bundle()` per room | Solver is pure and stateless — parallelises trivially |
| Dealer quote export | `/api/design` JSON payload | SKUs, prices and verified plan already in the response |
| Layout A/B options | `arrange_with_repair()` at higher temperature | Verifier makes aggressive sampling safe |

---

## Known limitations

- Catalogue is a 16-product representative sample, not a live product feed
- Rectangular rooms only; one fixed door position (bottom-left, 30-inch swing)
- Water savings modelled from published ratings, not metered usage data
- Project history is session-scoped; no database or multi-user authentication

---

## Business alignment

| Commitment | What a design tool must do | How Plumbline delivers it |
|---|---|---|
| Design excellence | Theme fit and spatial quality as first-class objectives | Theme-weighted ranking; per-theme arrangement guidance in the LLM prompt |
| Water conservation | Efficiency as a hard constraint, not a badge | Per-product WaterSense check; modelled annual savings vs legacy baseline |
| Operational efficiency | Fewer rework cycles, quote-ready output | Non-compliant layouts caught at specification time — every rejected attempt in the trace is a rework cycle that never reached an installer |
| Manufacturer channel | Output specifiable through showroom/dealer | `/api/design` returns SKUs, prices, flow ratings and a verified plan in one payload |

---

## Notice

This repository is an independent student case-study prototype. It is not affiliated with or endorsed by any manufacturer. Product data is a representative sample compiled from public specifications for demonstration purposes only.

See [`NOTICE.md`](NOTICE.md) for full notice.
