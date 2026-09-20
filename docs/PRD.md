# Product Requirements Document: KOHLER AI Bathroom Designer & Planner

| | |
|---|---|
| **Track** | Track 1, KOHLER-MITWPU AI Lab Case Study |
| **Author** | Pooja Lingwat |
| **Repo** | https://github.com/poojawork102/kohler-ai-bathroom-designer |
| **Version** | 1.1 (19 Sept 2026, solver + UI rebuilt) |
| **Status legend** | ✅ Built · 🟡 Partial · ⬜ Planned |

---

## 1. Summary

A web tool that turns a plain-English request ("8x10 ft bathroom, ₹6L budget, Japandi, smart features") into a **budget-compliant, space-valid, shoppable Kohler bathroom bundle** with a scaled 2D floorplan, itemised bill of materials, and sustainability metrics.

**Design principle:** the LLM only *understands* the request. All maths (cost, footprint, clearance) is done by deterministic code, so the output can never violate the budget or the room.

## 2. Problem

| Pain point | Who feels it | Today |
|---|---|---|
| Fixtures don't fit the room (footprint, clearances, door swing) | Homeowners, designers | Found out at install |
| Style mismatch across toilet / shower / faucet / vanity | Homeowners | Needs a paid designer |
| Bundle exceeds budget | Homeowners | Manual spreadsheet |
| No visibility of water / energy impact | Eco-conscious buyers | Not shown at purchase |

## 3. Goals and non-goals

**Goals**
1. Prompt → valid bundle + floorplan in under 2 seconds.
2. Zero budget or space violations in any returned bundle.
3. Runs with one command, no API key required (fallback parser).
4. Evaluators can understand the project in under 60 seconds from the README.

**Non-goals (v1)**
- Real checkout / cart, live Kohler pricing API, 3D rendering, CAD export.

## 4. Users

| Persona | Need |
|---|---|
| Homeowner (primary) | "Tell me what fits my room and budget" |
| Interior designer | Fast, defensible first-pass layout to show a client |
| Kohler retail / experience-centre staff | A guided-selling tool to use with walk-in customers |

## 5. Scope and functional requirements

| ID | Requirement | Priority | Status | Eval criterion |
|---|---|---|---|---|
| FR-1 | Parse NL prompt into `{length, width, budget, theme, household_size}` using an LLM with strict JSON schema; fall back to regex if no key or on failure | P0 | 🟡 regex only | Approach & Innovation |
| FR-2 | Structured inputs (sliders / dropdowns) as an alternative to free text | P1 | ✅ | Usability |
| FR-3 | Solver picks one item per category (toilet, shower, vanity, faucet) with **total cost ≤ budget** | P0 | ✅ | Technical Execution |
| FR-4 | Solver enforces **total footprint ≤ 40% of floor area** | P0 | ✅ | Technical Execution |
| FR-5 | Solver enforces **clearances** (toilet side ≥ 15 in, front ≥ 21 in; shower/vanity front clearance) as placement rules | P0 | ✅ | Technical Execution |
| FR-6 | If no valid bundle exists, return a clear message and the closest alternative (never silently return an invalid one) | P0 | ✅ | Technical Execution |
| FR-7 | Theme matching (Japandi / Minimalist Modern / Classic Luxury) and finish matching across items | P1 | 🟡 theme only | Approach & Innovation |
| FR-8 | 2D floorplan at true scale: room walls, door swing, fixtures at real dimensions, clearance zones, no overlaps | P0 | ✅ (drag-and-drop is post-deadline) | Approach & Innovation |
| FR-9 | Itemised BOM with SKU, price, dimensions, finish, total | P0 | ✅ | Technical Execution |
| FR-10 | Space-utilisation score | P1 | ✅ | Approach & Innovation |
| FR-11 | Annual water use vs legacy baseline, driven by household size | P1 | ✅ | Approach & Innovation |
| FR-12 | Wellness tags per product (e.g. Dekoda-compatible, circadian lighting), shown as labels | P2 | 🟡 data only | Approach & Innovation |
| FR-13 | Export: JSON config, printable spec sheet | P2 | ⬜ | Usability |
| FR-14 | Multi-page UI: Home, Planner, Sustainability, BOM | P1 | 🟡 shared base template + nav done; Planner page live | Usability |

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | End-to-end response < 2 s (local catalog, no DB) |
| Reliability | `pip install -r requirements.txt && python app.py` works on a clean machine |
| Determinism | Same input → same bundle (LLM at temperature 0, solver has no randomness) |
| Testability | `python -m pytest tests/` covers solver constraints and parser fallback |
| Accessibility | Colour contrast ≥ 4.5:1, keyboard-focusable controls |
| Responsiveness | Usable from 360 px to 1440 px width |

## 7. Architecture

```
User prompt
   │
   ▼
parser.py     LLM (JSON schema, temp 0)  ──fail/no key──▶  regex fallback
   │  {length, width, budget, theme, household}
   ▼
solver.py     catalog.json → filter by theme → pick bundle
              checks: cost ≤ budget · footprint ≤ 40% · clearances
              computes: utilisation %, water use, wellness tags
   │  bundle + metrics
   ▼
layout.py     places fixtures on walls, checks overlaps, returns coordinates
   │
   ▼
Flask (app.py) → /api/design (JSON) → templates/*.html + static/js (canvas)
```

## 8. Data model (catalog.json)

Each product: `id, name, category, sku, price_inr, dimensions_in{width,depth,height}, clearance_req_in{side_min,front_min}, gpf | gpm, aesthetic_themes[], finishes[], smart_features[], health_features[], source_url`.

Requirements on the data:
- Minimum **4 products per category** (16+ total) so the solver has real choices.
- Prices in **INR**, matching kohler.co.in.
- Every SKU verified against kohler.co.in; `source_url` filled in.

## 9. Information architecture

| Page | Route | Purpose |
|---|---|---|
| Home | `/` | Hero, how it works in 3 steps, theme cards, CTA |
| Planner | `/planner` | Prompt + sliders, live floorplan, metrics |
| Sustainability | `/sustainability` | Water comparison chart, wellness tags |
| Bill of Materials | `/summary` | Itemised list, totals, export |

## 10. Design requirements

- Visual language follows kohler.co.in: light, white-dominant, black type and CTAs, generous whitespace, restrained accent colour.
- Floorplan drawn as an architectural drawing: thin black walls, light-grey fixtures, dashed clearance zones.
- Errors and violations shown in plain language, never hidden.
- Design tokens live in `static/css/kohler.css` (single source of truth).

## 11. Success metrics

| Metric | Target | How verified |
|---|---|---|
| Budget violations | 0 across 50 random test inputs | `tests/test_solver.py` |
| Space violations | 0 across 50 random test inputs | `tests/test_solver.py` |
| Parse success (valid JSON) | 100% incl. fallback | `tests/test_parser.py` |
| Latency | < 2 s | manual + logged in response |
| Cold-start setup | ≤ 3 commands | README quick start |

## 12. Known issues

| # | Issue | Status |
|---|---|---|
| 1 | Old greedy solver could exceed the budget (a $10,000 brief returned $10,180) | ✅ Fixed: full search, guarantee tested (`tests/test_solver.py`) |
| 2 | Clearance rules were in the catalog but not enforced | ✅ Fixed: `layout.py` enforces front/side clearance and door swing |
| 3 | No LLM call; parser is regex only | ⬜ Open (FR-1) |
| 4 | Water formula mixed faucet flow into shower minutes | ✅ Fixed: toilet, shower, faucet modelled separately |
| 5 | Catalog too small (5 items, USD, unverified SKUs); only 1 of 4 items matches "Classic Luxury" | ⬜ Open: expand to 16+, INR, verify on kohler.co.in |
| 6 | UI ignored infeasible results | ✅ Fixed: explanatory banner plus closest alternative |

## 13. Milestones

| When | Deliverable |
|---|---|
| 19 Sept | Repo cleanup, README, fix issues 1, 2, 6, restyle to Kohler palette |
| 20 Sept | LLM parser + fallback, expanded catalog, video, Prompts PDF, 4-slide deck, email sent |
| 21 Sept | Buffer, rehearse demo, prepare interview answers |
| 22–23 Sept | Interviews, Kohler office, Kharadi |
| After | Multi-page UI polish, drag-and-drop layout, export |

## 14. Submission deliverables

| Deliverable | Location | Status |
|---|---|---|
| Working code | GitHub repo | 🟡 |
| Prompts documentation | `docs/Prompts_Documentation.pdf` | ⬜ |
| 4-slide pitch deck | `docs/Presentation_Deck.pdf` | ⬜ |
| 1–3 min demo video | link in README | ⬜ |
| Submission email | to Kohler contact, subject `AI Lab KOHLER-MITWPU Case Study - (PRN_Name)` | ⬜ |

## 15. Risks

| Risk | Mitigation |
|---|---|
| LLM API fails during live demo | Regex fallback is automatic; demo works offline |
| Wrong SKU or price spotted by Kohler staff | Verify each item on kohler.co.in, include `source_url` |
| UI rebuild breaks working demo | Do it on a branch, merge only when tests pass |
| Time (deadline 20 Sept) | Priority order in Section 13; multi-page polish is post-deadline |
