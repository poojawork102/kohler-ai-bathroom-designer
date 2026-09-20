"""Deterministic fixture placement (no AI, no randomness).

Coordinates are in INCHES. Origin is the top-left of the room, x grows to the
right, y grows downward. The room is `width_in` (x) by `length_in` (y).

Rules enforced here
-------------------
1. Every floor fixture (toilet, shower, vanity) sits with its back against a wall.
2. Each fixture has a "clearance envelope": its own footprint plus the free
   space it needs in front of it (`front_min`) and beside it (`side_min`,
   measured from the fixture centreline - e.g. toilet centreline >= 15 in
   from the wall or the next fixture).
3. An envelope must lie fully inside the room and must not overlap any OTHER
   fixture's footprint. (Envelopes may overlap each other - two people don't
   use two fixtures at the same moment.)
4. Nothing may sit inside the door-swing square (bottom-left corner).
5. Faucets are mounted on the vanity, so they take no floor space.
"""

EPS = 1e-6
DOOR_WIDTH_IN = 30.0      # door leaf width == door-swing square side
STEP_IN = 6.0             # spacing of candidate positions along a wall
MAX_NODES = 15000         # search budget per layout attempt (keeps latency bounded)

PLACE_ORDER = ("shower", "toilet", "vanity")
WALL_PREFERENCE = {
    "shower": ("top", "right", "left", "bottom"),
    "toilet": ("top", "left", "right", "bottom"),
    "vanity": ("left", "right", "bottom", "top"),
}


# ---------------------------------------------------------------- geometry --
def door_keepout(length_in):
    """Square swept by the door leaf: bottom-left corner of the room."""
    return (0.0, length_in - DOOR_WIDTH_IN, DOOR_WIDTH_IN, DOOR_WIDTH_IN)


def overlaps(a, b):
    """Rectangles are (x, y, w, h). Touching edges do NOT count as overlap."""
    return (a[0] < b[0] + b[2] - EPS and b[0] < a[0] + a[2] - EPS and
            a[1] < b[1] + b[3] - EPS and b[1] < a[1] + a[3] - EPS)


def inside(r, width_in, length_in):
    return (r[0] >= -EPS and r[1] >= -EPS and
            r[0] + r[2] <= width_in + EPS and r[1] + r[3] <= length_in + EPS)


def _to_room(wall, u0, v0, span_u, span_v, width_in, length_in):
    """Map a rectangle from wall-local coords to room coords.

    u runs ALONG the wall, v runs from the wall INTO the room.
    """
    if wall == "top":
        return (u0, v0, span_u, span_v)
    if wall == "bottom":
        return (u0, length_in - v0 - span_v, span_u, span_v)
    if wall == "left":
        return (v0, u0, span_v, span_u)
    return (width_in - v0 - span_v, u0, span_v, span_u)  # right


def _positions(wall_len, size):
    """Candidate start positions along a wall: corners first, then every STEP_IN."""
    max_t = wall_len - size
    if max_t < -EPS:
        return []
    raw = [0.0, max_t]
    t = STEP_IN
    while t < max_t - EPS:
        raw.append(t)
        t += STEP_IN
    seen, out = set(), []
    for t in raw:
        key = round(t, 3)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def _candidates(fx, width_in, length_in):
    w, d = fx["width"], fx["depth"]
    half = max(w / 2.0, fx["side_min"])
    for wall in WALL_PREFERENCE[fx["category"]]:
        wall_len = width_in if wall in ("top", "bottom") else length_in
        for t in _positions(wall_len, w):
            cx = t + w / 2.0
            yield {
                "wall": wall,
                "u": t,
                "foot": _to_room(wall, t, 0.0, w, d, width_in, length_in),
                "env": _to_room(wall, cx - half, 0.0, 2 * half, d + fx["front_min"],
                                width_in, length_in),
            }


# ---------------------------------------------------------------- placement --
def place_fixtures(width_in, length_in, fixtures):
    """Find a valid layout or return None.

    fixtures: list of dicts with keys
        category ('shower'|'toilet'|'vanity'), width, depth, side_min, front_min
    Returns a list of placement dicts (same order as PLACE_ORDER) or None.
    """
    W, L = float(width_in), float(length_in)
    door = door_keepout(L)
    order = sorted(fixtures, key=lambda f: PLACE_ORDER.index(f["category"]))
    placed, nodes = [], [0]

    def fits(c):
        if overlaps(c["foot"], door) or not inside(c["env"], W, L):
            return False
        for p in placed:
            if (overlaps(c["foot"], p["foot"]) or overlaps(c["env"], p["foot"])
                    or overlaps(c["foot"], p["env"])):
                return False
        return True

    def search(i):
        if i == len(order):
            return True
        for c in _candidates(order[i], W, L):
            nodes[0] += 1
            if nodes[0] > MAX_NODES:
                return False
            if fits(c):
                placed.append(dict(c, fx=order[i]))
                if search(i + 1):
                    return True
                placed.pop()
        return False

    if not search(0):
        return None

    out = []
    for p in placed:
        fx = p["fx"]
        x, y, w, d = p["foot"]
        ex, ey, ew, ed = p["env"]
        out.append({
            "category": fx["category"], "side": p["wall"], "u": round(p["u"], 2),
            "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "d": round(d, 2),
            "u_len": fx["width"], "v_len": fx["depth"],
            "clearance": {"x": round(ex, 2), "y": round(ey, 2),
                          "w": round(ew, 2), "d": round(ed, 2)},
        })
    return out


def mount_faucet(fx, vanity, width_in, length_in):
    """Centre the faucet on the vanity's back edge (against the wall)."""
    if fx["width"] > vanity["u_len"] or fx["depth"] > vanity["v_len"]:
        return None
    u0 = vanity["u"] + (vanity["u_len"] - fx["width"]) / 2.0
    x, y, w, d = _to_room(vanity["side"], u0, 2.0, fx["width"], fx["depth"],
                          float(width_in), float(length_in))
    return {"category": "faucet", "side": vanity["side"], "mounted_on": "vanity",
            "x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "d": round(d, 2)}


def verify_layout(placements, width_in, length_in):
    """Independent re-check of a finished layout. Returns a list of problems ([] = valid)."""
    W, L = float(width_in), float(length_in)
    problems = []
    floor = [p for p in placements if p["category"] != "faucet"]
    door = door_keepout(L)
    for p in floor:
        foot = (p["x"], p["y"], p["w"], p["d"])
        c = p["clearance"]
        env = (c["x"], c["y"], c["w"], c["d"])
        if not inside(foot, W, L):
            problems.append(f"{p['category']} footprint outside room")
        if not inside(env, W, L):
            problems.append(f"{p['category']} clearance zone outside room")
        if overlaps(foot, door):
            problems.append(f"{p['category']} blocks door swing")
        for q in floor:
            if q is p:
                continue
            qfoot = (q["x"], q["y"], q["w"], q["d"])
            if overlaps(foot, qfoot):
                problems.append(f"{p['category']} overlaps {q['category']}")
            if overlaps(env, qfoot):
                problems.append(f"{p['category']} clearance blocked by {q['category']}")
    return problems
