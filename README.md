# Plumbline

**Conversational bathroom design with verified spatial compliance**

A conversational bathroom design engine that turns a sentence like *"8x10 spa
bathroom for a family of four, 6 lakh budget, touchless"* into a costed,
code-compliant, WaterSense-certified floor plan — with the AI's own reasoning
shown and independently verified.

**Video walkthrough:** https://youtu.be/OoWaedDzoKU
**Prompts documentation:** [docs/Prompts.md](docs/Prompts.md)
**Pitch deck:** [Plumbline_Deck.pdf](Plumbline_Deck.pdf)
**Product Requirements:** [docs/PRD.md](docs/PRD.md)

---

## The core idea: constrain the model, then verify it

Large language models are excellent at reading intent and making aesthetic
judgements, and unreliable at metric geometry. Ask Gemini for fixture
coordinates in inches and it will cheerfully overlap a toilet with a shower.

Two common responses to that are both wrong. Bypassing the LLM throws away the
design reasoning that makes the product worth building. Clamping its output to
the walls hides collisions instead of resolving them.

This build does neither. It **narrows the model's action space** and puts a
**deterministic verifier in the loop**:

| Stage | Owner | What happens |
|---|---|---|
| 1. Understand | Gemini | Free text → structured brief (dimensions, budget, theme, household). Regex parser is the fallback. |
| 2. Select | Python | Enumerates all 256 catalogue bundles, filters by budget and floor-area limit, ranks by theme fit / water / smart features. **Cannot** return an over-budget bundle. |
| 3. Arrange | Gemini | Proposes a layout as `(wall, offset-along-wall)` per fixture — **never raw x/y**. Coordinates are derived by code, so an off-room or wrong-sized fixture is structurally impossible. |
| 4. Verify | Python | `layout.verify_layout()` independently re-checks clearances, door swing and overlaps, and returns a plain-English violation list. |
| 5. Repair | Gemini | Violations are fed back as a critique. The model retries, forbidden from repeating the rejected arrangement. Bounded at 2 repairs. |
| 6. Fall back | Python | If the model still fails, a constraint search ships a guaranteed-valid layout. **A user never sees a broken plan.** |
| 7. Narrate | Gemini | Writes the rationale using *only* the verified numbers, so it cannot invent a saving figure. |

The self-correction trace is returned in the API response under `data.ai.trace`
and rendered in the UI — you can watch the model get it wrong and fix itself.

### Why the constrained action space matters

Free coordinates give the model a 2-DOF continuous space per fixture with no
notion of "against a wall". `(wall, offset)` is 1 discrete + 1 bounded
continuous choice, and the offset is clipped to the wall run in code. That
single change eliminates out-of-bounds and floating fixtures entirely, leaving
the verifier to catch only the interesting failure — inter-fixture clearance
conflicts — which is exactly what the repair loop is for.

---

## Sustainability is a hard constraint, not a badge

Every design is certified against the **EPA WaterSense** specification that
KOHLER's own products are certified to (toilets ≤ 1.28 gpf, showerheads
≤ 2.0 gpm, lavatory faucets ≤ 1.5 gpm), with a per-product pass/fail report at
`data.watersense`. Annual water saving is modelled per fixture class against a
legacy 3.5 gpf / 2.5 gpm baseline, scaled by household size — a typical
family-of-four design saves ~27,900 gallons a year.

This maps directly onto KOHLER's mission to help people live *gracious, healthy
and sustainable lives* and the **Believing in Better** commitment to net-zero
environmental impact by 2035.

---

## Quickstart

```bash
git clone https://github.com/poojawork102/plumbline.git
cd plumbline

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # paste your Gemini key (optional)
python app.py                     # http://localhost:5000
```

**The app runs with no API key.** Without one it uses the regex intent parser
and the deterministic layout engine, and every page still works — the AI stages
degrade, they never crash. `GET /api/health` reports whether the LLM path is
live:

```json
{"status":"ok","gemini":"live","model":"gemini-2.5-flash","catalog":16}
```

Run the tests:

```bash
python -m pytest tests/ -q        # 22 passing
python tests/test_ai_engine.py    # proves the repair loop with a stubbed model
```

---

## Project layout

```
app.py             Flask routes + the 7-stage design pipeline
ai_engine.py       Gemini calls, constrained generation, verify→repair loop
solver.py          Deterministic bundle selection (budget, water, theme)
layout.py          Geometry, clearance envelopes, independent verifier
intent_parser.py   Regex intent parser (offline fallback)
catalog.json       16 products with real SKUs, flow rates, clearances
templates/         Planner, sustainability dashboard, landing page
tests/             22 unit tests incl. a stubbed-model AI loop test
```

---

## Scope and scalability

**Shipped in this prototype**
- Natural-language intake with graceful offline degradation
- 256-combination deterministic bundle solver with infeasibility explanations
- LLM layout generation with verify → repair → fallback
- WaterSense certification report and annual water/cost savings
- SVG floor plan, print-to-PDF specification sheet, session project history

**Designed for, not built tonight** — each is a known extension point, not a rewrite:

| Extension | Where it plugs in | Why it scales |
|---|---|---|
| Live SKU catalogue | `load_catalog()` → KOHLER PIM/API | Solver is catalogue-agnostic; only the loader changes. |
| Multi-room / whole-home | `solve_bathroom_bundle()` per room | Solver is pure and stateless — parallelises trivially. |
| Regional plumbing codes | `layout.py` constants → code profile per market | Clearances are already data, not logic (IS 1172 for India, IBC/ADA for US). |
| Dealer quote export | `/api/design` JSON | Response already carries SKUs, prices and a verified plan. |
| Layout A/B options | run `arrange_with_repair` at higher temperature, N times | Verifier makes it safe to sample aggressively — invalid options are dropped, not shown. |
| Cost control at scale | cache verified layouts by room geometry | Identical room dimensions reuse a plan; the LLM is called only for novel geometry. |

**Honest limitations**
- Catalogue is a 16-product representative sample, not the live KOHLER range.
- Water savings use published flow ratings and modelled usage, not metered data.
- Project history is session-scoped; no database or multi-user auth yet.
- One door position (bottom-left) and rectangular rooms only.

## How this aligns with a manufacturer's business

| Commitment | What it demands of a design tool | How Plumbline delivers it |
|---|---|---|
| Design excellence | Theme fit and spatial quality as first-class objectives, not just lowest compliant cost | Theme-weighted ranking in `solver._rank_key`; per-theme arrangement guidance in the LLM prompt |
| Water conservation | Efficiency as a hard constraint, not a badge | Per-product WaterSense check (toilet ≤1.28 gpf, shower ≤2.0 gpm, faucet ≤1.5 gpm); modelled annual savings against a legacy baseline |
| Operational efficiency | Fewer rework cycles, faster time-to-specify, quote-ready output | Non-compliant layouts are caught at specification time by the verifier, not on site by an installer — every rejected attempt in the trace is a rework cycle that never happened |
| Manufacturer, not software company | Output must be specifiable through a real showroom/dealer channel | `/api/design` returns SKUs, prices, flow ratings and a verified plan in one payload |

Plumbline was built to advance widely recognized public commitments, such as achieving a net zero environmental impact by 2035, accelerating water-saving product development, and supporting EPA WaterSense certification standards. This project serves as an independent technical demonstration and does not claim any official partnership, endorsement, or inside knowledge of internal manufacturer operations.
