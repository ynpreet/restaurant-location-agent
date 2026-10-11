#!/usr/bin/env python3
"""
Restaurant Location Agent — Demo 2 of 4, Agentic AI Workshop.

USER STORY: "I want to open a Chinese restaurant — where exactly should I open it?"

A pure-Python (stdlib only) simulation of an agentic location scout.
The Planner decomposes the goal into tasks, calls tools, and a
Synthesizer recommends one Phoenix-area zip code with per-factor
scores and a plain-English explanation.

Business rules applied:
  1. Review-quality signals by area (stars + review text sentiment).
  2. Produce-cost / rent economics (cheaper produce + rent = cheaper to run).
  3. Customer / audience presence (foot traffic, demand).
  4. Hotelling competitor-proximity rule: a stall beside a competitor
     outperforms an isolated one — but over-saturation hurts.
  5. Cuisine saturation vs. demand gap.

The shipped dataset is SAMPLE data (synthetic, Yelp-schema faithful) so
the demo runs fully offline. See README.md "Point this at your real
dataset" to swap in the real Yelp JSON.

Run:   python3 demo.py
No network, no API keys, no dependencies. Fully deterministic:
identical bytes on every run.
"""

import hashlib
import json
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# SAMPLE DATASET (synthetic, Yelp-schema faithful) — labeled clearly.
# ---------------------------------------------------------------------------
# Real schema this mirrors (Yelp open dataset):
#   businesses: business_id, name, city, state, postal_code, latitude,
#               longitude, stars, review_count, categories
#   reviews:    business_id, stars, text
#
# These ~60 businesses across 8 Phoenix-area zips are INVENTED so the demo
# runs offline. They are marked SAMPLE throughout this file and in output.
SAMPLE_DATA_DISCLAIMER = (
    "NOTE: All business data below is SAMPLE (synthetic) data in the Yelp "
    "schema, generated for this offline demo. See README.md to point the "
    "agent at your real Yelp dataset."
)

CITY = "Phoenix"
STATE = "AZ"

# Per-zip area profile: (area name, vibe, produce_cost_index, rent_index,
# foot-traffic score 0-100). Lower produce/rent index = cheaper to run.
# (In the real repo, these would be derived from review/cost data.)
ZIP_PROFILES = {
    "85003": ("Downtown Phoenix", "urban core", 1.05, 1.35, 92),
    "85004": ("Downtown South", "urban", 1.02, 1.15, 85),
    "85006": ("Midtown", "urban", 1.00, 1.00, 78),
    "85012": ("Uptown", "urban", 0.98, 1.05, 84),
    "85015": ("West Phoenix", "mixed", 0.90, 0.80, 66),
    "85018": ("Arcadia", "affluent urban", 1.08, 1.45, 88),
    "85251": ("Scottsdale", "affluent", 1.10, 1.50, 80),
    "85020": ("North Phoenix", "suburban", 0.93, 0.85, 60),
}

# (name, categories, stars, review_count) per zip. ~60 businesses total.
_RAW_BUSINESSES = {
    "85003": [
        ("Golden Wok", "Chinese, Restaurants", 3.8, 420),
        ("Roosevelt Row Tacos", "Mexican, Restaurants", 4.1, 890),
        ("Downtown Diner", "Diners, Restaurants", 3.9, 610),
        ("Copper Star Coffee", "Coffee & Tea, Food", 4.3, 350),
        ("Bianco Slice House", "Pizza, Restaurants", 4.2, 720),
        ("The Arrogant Butcher", "Steakhouses, Restaurants", 4.0, 540),
        ("Sushi Loft", "Sushi Bars, Restaurants", 3.9, 480),
        ("Mama's Soul Food", "Soul Food, Restaurants", 4.1, 300),
    ],
    "85004": [
        ("Panda Express Lane", "Chinese, Restaurants", 3.6, 520),
        ("Jade Garden", "Chinese, Restaurants", 4.0, 380),
        ("Taco Guild Hall", "Mexican, Restaurants", 4.2, 810),
        ("Burrito Brothers", "Mexican, Restaurants", 4.0, 450),
        ("Phoenix Ale House", "Bars, American", 3.8, 390),
        ("Noodle & Co Corner", "Noodles, Restaurants", 3.7, 260),
        ("Sub Central", "Sandwiches, Food", 3.9, 340),
    ],
    "85006": [
        ("Szechuan Palace", "Szechuan, Chinese, Restaurants", 4.2, 640),
        ("Dragon Boat", "Chinese, Restaurants", 3.9, 410),
        ("Lucky Chopsticks", "Chinese, Restaurants", 3.7, 290),
        ("Beijing House", "Chinese, Restaurants", 4.0, 350),
        ("Midtown Grill", "American, Restaurants", 4.1, 560),
        ("Pho 88", "Vietnamese, Restaurants", 4.3, 620),
        ("Burger Theory", "Burgers, Restaurants", 3.8, 330),
        ("Salad Works", "Salads, Food", 3.9, 210),
    ],
    "85012": [
        ("Golden Lotus", "Cantonese, Chinese, Restaurants", 4.4, 780),
        ("Sichuan Hot Pot House", "Szechuan, Chinese, Restaurants", 4.3, 690),
        ("Dim Sum Central", "Dim Sum, Chinese, Restaurants", 4.2, 540),
        ("Uptown Pizza", "Pizza, Restaurants", 4.1, 480),
        ("Taco Libre", "Mexican, Restaurants", 4.0, 520),
        ("Green Bowl Salad", "Salads, Food", 4.2, 310),
        ("Craft Burger Co", "Burgers, Restaurants", 3.9, 440),
        ("Thai Orchid", "Thai, Restaurants", 4.3, 590),
    ],
    "85015": [
        ("China Star", "Chinese, Restaurants", 3.7, 460),
        ("Lucky Dragon", "Chinese, Restaurants", 3.6, 320),
        ("Tacos El Gordo", "Mexican, Restaurants", 4.2, 950),
        ("Maryvale Diner", "Diners, Restaurants", 3.8, 410),
        ("Pollo Asado", "Chicken, Restaurants", 4.0, 530),
        ("Pho Saigon", "Vietnamese, Restaurants", 4.1, 480),
        ("Westside Burgers", "Burgers, Restaurants", 3.7, 290),
    ],
    "85018": [
        ("Jade Emperor", "Chinese, Restaurants", 4.5, 810),
        ("Ming Dynasty", "Chinese, Restaurants", 4.4, 720),
        ("Peking Garden", "Chinese, Restaurants", 4.3, 560),
        ("Golden Dragon", "Chinese, Restaurants", 4.2, 480),
        ("Wok & Roll", "Chinese, Restaurants", 4.1, 390),
        ("Arcadia Steakhouse", "Steakhouses, Restaurants", 4.4, 690),
        ("Farm & Craft", "American, Restaurants", 4.2, 540),
        ("La Grande Orange", "Cafes, Restaurants", 4.3, 470),
    ],
    "85251": [
        ("China Chili", "Szechuan, Chinese, Restaurants", 4.3, 700),
        ("Great Wall", "Chinese, Restaurants", 4.2, 610),
        ("Szechuan Garden", "Chinese, Restaurants", 4.4, 680),
        ("Panda House", "Chinese, Restaurants", 4.1, 430),
        ("Dragon Phoenix", "Chinese, Restaurants", 4.0, 380),
        ("Noodle King", "Noodles, Chinese, Restaurants", 4.2, 520),
        ("Scottsdale Bistro", "French, Restaurants", 4.3, 560),
        ("Old Town Tacos", "Mexican, Restaurants", 4.2, 640),
    ],
    "85020": [
        ("China Kitchen", "Chinese, Restaurants", 3.8, 350),
        ("Northside Grill", "American, Restaurants", 4.0, 420),
        ("Suburban Pizza", "Pizza, Restaurants", 3.9, 380),
        ("Taco Time North", "Mexican, Restaurants", 3.8, 300),
        ("Sandwich Stop", "Sandwiches, Food", 3.7, 240),
        ("Pho North", "Vietnamese, Restaurants", 4.0, 310),
    ],
}

# Sample reviews (SAMPLE data) attached to Chinese competitors, used for the
# review-quality text signal. Format: (business name, stars, text).
_RAW_REVIEWS = [
    ("Golden Wok", 4, "Fresh vegetables and authentic flavors, quick lunch."),
    ("Golden Wok", 3, "Decent, but a bit greasy on busy nights."),
    ("Panda Express Lane", 3, "Fast and cheap, quality is hit or miss."),
    ("Jade Garden", 4, "Clean, fresh dumplings, family favorite."),
    ("Szechuan Palace", 5, "Incredibly fresh ingredients, real Szechuan heat."),
    ("Szechuan Palace", 4, "Authentic mapo tofu, very fresh produce."),
    ("Dragon Boat", 4, "Solid lunch special, fresh spring rolls."),
    ("Lucky Chopsticks", 3, "Okay takeout, noodles a little stale late night."),
    ("Beijing House", 4, "Fresh and tasty, good value."),
    ("Golden Lotus", 5, "The freshest Chinese food in the valley, authentic dim sum."),
    ("Golden Lotus", 5, "Amazing fresh seafood, authentic Cantonese."),
    ("Sichuan Hot Pot House", 5, "Fresh ingredients, authentic broth, packed every night."),
    ("Dim Sum Central", 4, "Great fresh carts on weekends, authentic."),
    ("Dim Sum Central", 3, "Good when fresh, gets greasy by afternoon."),
    ("China Star", 3, "Cheap and filling, nothing special."),
    ("Lucky Dragon", 3, "Average takeout, food sat under heat lamp."),
    ("Jade Emperor", 5, "Top-tier, fresh and refined, worth the price."),
    ("Ming Dynasty", 5, "Elegant and authentic, very fresh."),
    ("Peking Garden", 4, "Fresh Peking duck, solid menu."),
    ("Wok & Roll", 4, "Fun spot, fresh wok flavors."),
    ("China Chili", 4, "Spicy and fresh, great Szechuan."),
    ("Great Wall", 4, "Reliable, fresh lunch portions."),
    ("China Kitchen", 4, "Neighborhood favorite, fresh enough for the price."),
    ("China Kitchen", 3, "Fine for takeout, can be greasy."),
]

POSITIVE_WORDS = {"fresh", "authentic", "amazing", "excellent", "fantastic",
                  "love", "best", "incredib", "delicious", "favorite"}
NEGATIVE_WORDS = {"greasy", "stale", "bland", "cold", "slow", "dirty",
                  "overpriced", "soggy", "salty"}


def _build_dataset():
    businesses = []
    name_to_id = {}
    for z in sorted(_RAW_BUSINESSES):
        for i, (name, cats, stars, rc) in enumerate(_RAW_BUSINESSES[z], 1):
            bid = "b_%s_%02d" % (z, i)
            name_to_id[name] = bid
            businesses.append({
                "business_id": bid, "name": name, "city": CITY, "state": STATE,
                "postal_code": z, "latitude": 33.45 + i * 0.001,
                "longitude": -112.07 - i * 0.001, "stars": stars,
                "review_count": rc, "categories": cats,
            })
    reviews = []
    for i, (name, stars, text) in enumerate(_RAW_REVIEWS, 1):
        reviews.append({"review_id": "r_%03d" % i,
                        "business_id": name_to_id[name],
                        "stars": stars, "text": text})
    return businesses, reviews


BUSINESSES, REVIEWS = _build_dataset()


def is_chinese(b):
    return "Chinese" in b["categories"]


# ---------------------------------------------------------------------------
# Input honesty guards — the demo must not invent facts, silently assume
# missing context, or pretend a recompute happened. These checks run before
# planning and only add output for inputs outside the two canned turns, so
# the canned demo's bytes are unchanged.
# ---------------------------------------------------------------------------
_KNOWN_CUISINES = ("chinese", "italian", "mexican", "indian", "thai",
                   "american", "japanese", "vietnamese", "korean", "sushi",
                   "vegetarian", "vegan", "pizza", "seafood", "french",
                   "greek", "turkish", "bubble tea", "taco", "cantonese",
                   "szechuan", "dim sum")
_KNOWN_CITIES = ("phoenix", "tempe", "scottsdale", "mesa", "chandler",
                 "gilbert", "glendale", "peoria", "arizona")
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3}\s+"
    r"(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|"
    r"Way|Plaza|Court|Ct|Circle|Cir)\b")
_AVOID_RE = re.compile(r"avoid[^.?!]{0,80}competit", re.IGNORECASE)


def _detect_avoid_competition(goal):
    """Infer the blue-ocean strategy from the goal text itself."""
    g = goal.lower()
    return bool(_AVOID_RE.search(goal)) or "blue ocean" in g \
        or "quietest" in g


def _asks_exact_live_facts(goal):
    """True when the user demands exact, current, address-level facts."""
    g = goal.lower()
    return bool(_ADDRESS_RE.search(goal)) or \
        ("exact" in g and "current" in g) or \
        "do not use estimates" in g or "no estimates" in g


def _refuse_exact_facts():
    print()
    print("UNABLE TO ANSWER AS ASKED")
    print("-" * 70)
    print("You asked for exact, current, address-level facts (rent dollars,")
    print("foot-traffic counts, competitor counts at a specific street")
    print("address). This demo cannot provide them:")
    print("  - The dataset is SAMPLE (synthetic): ~60 invented businesses")
    print("    across 8 Phoenix ZIPs — no street addresses exist in it.")
    print("  - 'Rent' here is a relative index (1.00 = baseline), not dollars.")
    print("  - 'Foot traffic' is a synthetic 0-100 proxy, not a live count.")
    print("Giving you numbers would mean inventing them. To answer for a")
    print("real address, point the agent at a real dataset (see README.md")
    print("section 10, 'Point this at your real dataset').")


def _missing_context_notes(goal, cuisine):
    """Name context the goal left out so scoring never assumes silently."""
    g = goal.lower()
    notes = []
    if not any(c in g for c in _KNOWN_CUISINES):
        notes.append("no cuisine named — assuming '%s' (demo default; pass a "
                     "different cuisine= to change it)" % cuisine)
    if not (any(c in g for c in _KNOWN_CITIES)
            or re.search(r"\bAZ\b", goal) or re.search(r"\b\d{5}\b", goal)):
        notes.append("no city named — assuming Phoenix AZ (the demo dataset "
                     "covers 8 Phoenix-area ZIPs)")
    return notes


def _cuisine_coverage_note(cuisine):
    """Disclose what the sample dataset cannot measure for this cuisine."""
    if cuisine.strip().lower() == "chinese":
        return None
    w = DEFAULT_WEIGHTS
    return (
        "DATA LIMITATIONS — the sample dataset labels competitors and "
        "reviews for Chinese cuisine only, so for '%s':\n"
        "  1. competitor counts and demand sentiment are NOT measured for "
        "this cuisine — the engine reuses the Chinese-labeled evidence as "
        "a structural stand-in;\n"
        "  2. rent/produce are relative synthetic indexes (1.00 = baseline), "
        "not dollar amounts;\n"
        "  3. foot-traffic is a synthetic 0–100 proxy, not measured counts;\n"
        "  4. no '%s'-specific demand signal exists in this sample.\n"
        "Scoring weights — how each factor moves the ranking: quality %.2f, "
        "economics %.2f, audience %.2f, hotelling %.2f, gap %.2f."
        % (cuisine, cuisine, w["quality"], w["economics"], w["audience"],
           w["hotelling"], w["gap"]))


# ---------------------------------------------------------------------------
# Agent memory — remembers past queries and reuses the scoring profile.
# ---------------------------------------------------------------------------
@dataclass
class Memory:
    past_queries: List[Dict[str, Any]] = field(default_factory=list)
    scoring_profile: Dict[str, float] = field(default_factory=dict)

    def record(self, query, cuisine, weights, winner):
        self.past_queries.append({"query": query, "cuisine": cuisine,
                                  "weights": dict(weights), "winner": winner})

    def consult(self, cuisine):
        for q in reversed(self.past_queries):
            if q["cuisine"] == cuisine:
                return q
        return None


# Seeded memory: two earlier (fixed, deterministic) sessions.
def seed_memory():
    mem = Memory()
    mem.record("Bubble tea shop in Tempe — best block?", "Bubble Tea",
               {"quality": 0.30, "economics": 0.20, "audience": 0.25,
                "hotelling": 0.10, "gap": 0.15}, "85281")
    mem.record("Taco truck near ASU campus?", "Mexican",
               {"quality": 0.20, "economics": 0.25, "audience": 0.30,
                "hotelling": 0.10, "gap": 0.15}, "85281")
    return mem


# ---------------------------------------------------------------------------
# Tools (what the planner can call)
# ---------------------------------------------------------------------------
class Tools:
    @staticmethod
    def fetch_area_data(postal_code):
        """Pull all businesses + the area profile for one zip."""
        prof = ZIP_PROFILES[postal_code]
        biz = [b for b in BUSINESSES if b["postal_code"] == postal_code]
        return {
            "postal_code": postal_code, "area": prof[0], "vibe": prof[1],
            "produce_cost_index": prof[2], "rent_index": prof[3],
            "foot_traffic": prof[4], "businesses": biz,
            "n_restaurants": len(biz),
        }

    @staticmethod
    def analyze_review_quality(area):
        """Rule 1: review-quality signals — weighted stars + review text."""
        biz = area["businesses"]
        total_rc = sum(b["review_count"] for b in biz)
        wstars = (sum(b["stars"] * b["review_count"] for b in biz) / total_rc
                  if total_rc else 0.0)
        bids = {b["business_id"] for b in biz if is_chinese(b)}
        pos = neg = 0
        for r in REVIEWS:
            if r["business_id"] in bids:
                t = r["text"].lower()
                pos += sum(1 for w in POSITIVE_WORDS if w in t)
                neg += sum(1 for w in NEGATIVE_WORDS if w in t)
        sentiment = (pos - neg) / max(1, pos + neg)  # -1..1
        quality_score = max(0.0, min(100.0, (wstars - 2.5) / 2.0 * 100.0))
        food_signal = max(0.0, min(100.0, 50.0 + sentiment * 50.0))
        return {"weighted_stars": round(wstars, 2),
                "quality_score": round(quality_score, 1),
                "chinese_review_sentiment": round(sentiment, 2),
                "food_signal": round(food_signal, 1),
                "n_chinese_reviews_scanned": sum(1 for r in REVIEWS
                                                if r["business_id"] in bids)}

    @staticmethod
    def analyze_competitors(area):
        """Rule 4: Hotelling — score peaks near, but not crowded by, rivals."""
        comps = [b for b in area["businesses"] if is_chinese(b)]
        n = len(comps)
        curve = {0: 30.0, 1: 65.0, 2: 90.0, 3: 100.0, 4: 95.0, 5: 70.0}
        hotelling = curve.get(n, 40.0) if n >= 6 else curve.get(n, 30.0)
        avg_comp_stars = (sum(b["stars"] for b in comps) / n) if n else 0.0
        avg_comp_reviews = (sum(b["review_count"] for b in comps) / n) if n else 0.0
        return {"n_chinese_competitors": n,
                "competitor_names": [b["name"] for b in comps],
                "avg_competitor_stars": round(avg_comp_stars, 2),
                "avg_competitor_reviews": round(avg_comp_reviews, 0),
                "hotelling_score": hotelling}

    @staticmethod
    def estimate_economics(area):
        """Rule 2: produce + rent economics. Cheaper inputs = cheaper to run."""
        cost = 0.6 * area["rent_index"] + 0.4 * area["produce_cost_index"]
        econ = max(0.0, min(100.0, (1.6 - cost) / 0.9 * 100.0))
        return {"produce_cost_index": area["produce_cost_index"],
                "rent_index": area["rent_index"],
                "blended_cost": round(cost, 2),
                "economics_score": round(econ, 1)}

    @staticmethod
    def assess_audience_and_gap(area, comps):
        """Rules 3 & 5: audience presence; cuisine saturation vs demand gap."""
        audience = area["foot_traffic"]
        n = comps["n_chinese_competitors"]
        saturation = n / max(1, area["n_restaurants"])
        demand = min(1.0, comps["avg_competitor_reviews"] / 800.0)
        gap = max(0.0, min(100.0, (demand * 0.7 - saturation * 1.4 + 0.45) * 100))
        return {"audience_score": audience,
                "saturation_pct": round(saturation * 100, 1),
                "demand_signal": round(demand * 100, 1),
                "gap_score": round(gap, 1)}


# ---------------------------------------------------------------------------
# Planner — decomposes the goal into tool-calling tasks.
# ---------------------------------------------------------------------------
@dataclass
class Task:
    step: int
    description: str
    tool: str
    args: Tuple = ()


class Planner:
    def plan(self, goal, zips, memory, cuisine):
        remembered = memory.consult(cuisine)
        note = ("No past %s queries. Using default scoring profile."
                % cuisine)
        if remembered:
            note = ("Memory hit: reused the '%s' scoring profile from "
                    "'%s' (winner was %s)." %
                    (remembered["cuisine"], remembered["query"],
                     remembered["winner"]))
        tasks = []
        step = 1
        for z in zips:
            tasks.append(Task(step, "Fetch area data for %s" % z,
                              "fetch_area_data", (z,)))
            step += 1
        tasks.append(Task(step, "Analyze review-quality signals per area",
                          "analyze_review_quality_all", ()))
        step += 1
        tasks.append(Task(step, "Analyze competitors (Hotelling) per area",
                          "analyze_competitors_all", ()))
        step += 1
        tasks.append(Task(step, "Estimate produce/rent economics per area",
                          "estimate_economics_all", ()))
        step += 1
        tasks.append(Task(step, "Score every candidate location",
                          "score_location_all", ()))
        step += 1
        tasks.append(Task(step, "Synthesize final recommendation",
                          "synthesize_recommendation", ()))
        return tasks, note


# ---------------------------------------------------------------------------
# The agent loop — prints PLAN and every step so the loop is visible.
# ---------------------------------------------------------------------------
class LocationAgent:
    def __init__(self, weights, avoid_competition=False, rent_shocks=None):
        self.weights = weights
        self.avoid_competition = avoid_competition
        self.rent_shocks = rent_shocks or {}
        self.areas = {}

    def run_step(self, task):
        t = task.tool
        if t == "fetch_area_data":
            area = Tools.fetch_area_data(task.args[0])
            shock = self.rent_shocks.get(area["postal_code"])
            shock_note = ""
            if shock:
                old = area["rent_index"]
                area["rent_index"] = round(old * shock, 4)
                shock_note = ("; RENT SHOCK x%.2f: rent_index %.2f -> %.2f"
                              % (shock, old, area["rent_index"]))
            self.areas[area["postal_code"]] = area
            a = area
            print("  [tool] fetch_area_data(%s) -> %s (%s): %d businesses, "
                  "foot-traffic %d%s" % (a["postal_code"], a["area"], a["vibe"],
                                         a["n_restaurants"],
                                         a["foot_traffic"], shock_note))
        elif t in ("analyze_review_quality_all", "analyze_competitors_all",
                   "estimate_economics_all"):
            for z in sorted(self.areas):
                area = self.areas[z]
                if t == "analyze_review_quality_all":
                    r = Tools.analyze_review_quality(area)
                    area["quality"] = r
                    print("  [tool] analyze_review_quality(%s) -> weighted "
                          "stars %.2f, chinese review sentiment %+.2f"
                          % (z, r["weighted_stars"],
                             r["chinese_review_sentiment"]))
                elif t == "analyze_competitors_all":
                    r = Tools.analyze_competitors(area)
                    area["comps"] = r
                    print("  [tool] analyze_competitors(%s) -> %d chinese "
                          "competitors, hotelling=%.0f"
                          % (z, r["n_chinese_competitors"],
                             r["hotelling_score"]))
                else:
                    r = Tools.estimate_economics(area)
                    area["econ"] = r
                    print("  [tool] estimate_economics(%s) -> produce %.2f, "
                          "rent %.2f, blended cost %.2f"
                          % (z, r["produce_cost_index"], r["rent_index"],
                             r["blended_cost"]))
        elif t == "score_location_all":
            for z in sorted(self.areas):
                self.score_location(z)
        elif t == "synthesize_recommendation":
            self.synthesize()

    def score_location(self, z):
        area = self.areas[z]
        comps = Tools.analyze_competitors(area)
        aud = Tools.assess_audience_and_gap(area, comps)
        area["aud"] = aud
        q = area["quality"]["quality_score"]
        e = area["econ"]["economics_score"]
        a = float(aud["audience_score"])
        if self.avoid_competition:
            h = max(0.0, 100.0 - comps["n_chinese_competitors"] * 20.0)
        else:
            h = comps["hotelling_score"]
        g = aud["gap_score"]
        w = self.weights
        total = w["quality"] * q + w["economics"] * e + w["audience"] * a \
            + w["hotelling"] * h + w["gap"] * g
        area["factors"] = {"quality": q, "economics": e, "audience": a,
                           "hotelling": h, "gap": g}
        area["total"] = round(total, 1)
        print("  [tool] score_location(%s) -> total %.1f "
              "[quality %.0f | economics %.0f | audience %.0f | "
              "hotelling %.0f | gap %.0f]"
              % (z, area["total"], q, e, a, h, g))

    def synthesize(self):
        ranked = sorted(self.areas.values(),
                        key=lambda x: (-x["total"], x["postal_code"]))
        best = ranked[0]
        runner = ranked[1]
        print()
        print("SYNTHESIZER — final recommendation")
        print("-" * 70)
        print("RECOMMENDED: %s (%s, %s %s)" %
              (best["postal_code"], best["area"], CITY, STATE))
        print("Score: %.1f/100  (runner-up %s at %.1f)"
              % (best["total"], runner["postal_code"], runner["total"]))
        print()
        print("Per-factor scores for %s:" % best["postal_code"])
        labels = {"quality": "1. Review-quality signals",
                  "economics": "2. Produce/rent economics",
                  "audience": "3. Customer/audience presence",
                  "hotelling": "4. Hotelling competitor-proximity",
                  "gap": "5. Cuisine saturation vs demand gap"}
        for k in ("quality", "economics", "audience", "hotelling", "gap"):
            print("  %-38s %5.1f/100" % (labels[k], best["factors"][k]))
        print()
        print("Why, in plain English:")
        for line in self.explain(best, runner):
            print(textwrap.fill("  " + line, width=70,
                                subsequent_indent="  "))
        self.best = best["postal_code"]

    def explain(self, best, runner):
        cost_note = ("cheapest zips to run in" if best["econ"]["blended_cost"] <= 0.95
                     else "mid-range operating costs" if best["econ"]["blended_cost"] <= 1.15
                     else "higher operating costs — downtown rents push it up, "
                          "but the customer numbers carry the case")
        comp_word = "competitor" if best["comps"]["n_chinese_competitors"] == 1 else "competitors"
        f = best["factors"]
        z = best["postal_code"]
        comps = ", ".join(best["comps"]["competitor_names"]) or "none"
        lines = []
        if self.avoid_competition:
            lines.append(
                "You asked to avoid heavy competition, so the agent re-"
                "weighted the plan: it now rewards LOW competitor counts "
                "instead of the usual Hotelling clustering.")
        lines += [
            "Review-quality signal: %s's restaurants average %.2f stars "
            "(weighted by review count), and local Chinese-spot reviews "
            "skew %s — diners here already trust the food quality."
            % (z, best["quality"]["weighted_stars"],
               "positive" if best["quality"]["chinese_review_sentiment"] >= 0
               else "negative"),
            "Economics: produce cost index %.2f and rent index %.2f give a "
            "blended operating cost of %.2f — %s."
            % (best["econ"]["produce_cost_index"], best["econ"]["rent_index"],
               best["econ"]["blended_cost"], cost_note),
            "Customers: foot-traffic/audience score %d/100 means the "
            "cheap setup actually has people walking past the door."
            % best["aud"]["audience_score"],
            "Hotelling: %d existing Chinese %s (%s). %s"
            % (best["comps"]["n_chinese_competitors"], comp_word, comps,
               "A small cluster already proves the cuisine draws crowds "
               "here — you join the draw instead of educating a cold "
               "market alone." if best["comps"]["n_chinese_competitors"]
               in (2, 3, 4) else "Room to be the anchor Chinese spot in "
               "the area."),
            "Saturation vs demand: only %.1f%% of restaurants here are "
            "Chinese, while demand signal is %d/100 — a real gap between "
            "what diners want and what's available."
            % (best["aud"]["saturation_pct"], best["aud"]["demand_signal"]),
            "Runner-up %s (%s) scored %.1f but lost on %s."
            % (runner["postal_code"], runner["area"], runner["total"],
               min(("quality", "economics", "audience", "hotelling", "gap"),
                   key=lambda k: runner["factors"][k])),
        ]
        return lines


# ---------------------------------------------------------------------------
# Demo script — two turns: the ask, then a follow-up reusing memory.
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS = {"quality": 0.25, "economics": 0.20, "audience": 0.20,
                   "hotelling": 0.15, "gap": 0.20}

ZIPS = sorted(ZIP_PROFILES)


def banner():
    print("=" * 70)
    print("RESTAURANT LOCATION AGENT — Demo 2 of 4, Agentic AI Workshop")
    print("=" * 70)
    print(SAMPLE_DATA_DISCLAIMER)
    print()


def _run_pass(goal, cuisine, memory, weights, avoid, rent_shocks,
              record):
    """One full plan→execute→synthesize pass. Returns the LocationAgent."""
    planner = Planner()
    tasks, note = planner.plan(goal, ZIPS, memory, cuisine)
    print()
    print("PLANNER — plan of action (%d steps)" % len(tasks))
    for t in tasks:
        print("  Step %2d. %-44s [tool: %s]" %
              (t.step, t.description, t.tool))
    print()
    print("MEMORY — %s" % note)
    print()
    print("EXECUTION — the agent loop, step by step")
    print("-" * 70)
    agent = LocationAgent(weights, avoid_competition=avoid,
                          rent_shocks=rent_shocks)
    for t in tasks:
        print("Step %2d: %s" % (t.step, t.description))
        agent.run_step(t)
        print()
    if record:
        memory.record(goal, cuisine, weights, agent.best)
    return agent


def _ranked(agent):
    return sorted(agent.areas.values(),
                  key=lambda x: (-x["total"], x["postal_code"]))


def turn(goal, cuisine, memory, weights, avoid_competition=False,
         label="TURN 1", rent_shock=None):
    print("=" * 70)
    print("%s — USER: %s" % (label, goal))
    print("=" * 70)
    # T3 guard: exact live facts at a street address — refuse, don't invent.
    if _asks_exact_live_facts(goal):
        _refuse_exact_facts()
        return None
    avoid = avoid_competition or _detect_avoid_competition(goal)
    # T4 guard: state assumptions instead of scoring on silent defaults.
    # A memory hit means this is a follow-up — context carries over.
    if memory.consult(cuisine) is None:
        missing = _missing_context_notes(goal, cuisine)
        if missing:
            print()
            print("MISSING INFO — stating assumptions before scoring:")
            for m in missing:
                print("  - %s." % m)
            print("  Re-ask naming a cuisine and city to change them.")
    # T2 guard: disclose what the sample data cannot measure.
    cov = _cuisine_coverage_note(cuisine)
    if cov:
        print()
        print(cov)
    agent = _run_pass(goal, cuisine, memory, weights, avoid, None, True)
    # T5: genuine recompute — re-run with a rent shock on the winner,
    # every other input unchanged, then report whether it still wins.
    if rent_shock:
        winner = agent.best
        print()
        print("=" * 70)
        print("SENSITIVITY — re-running with rent x%.2f in %s (the "
              "top-ranked ZIP); every other input unchanged"
              % (rent_shock, winner))
        print("=" * 70)
        agent2 = _run_pass(goal, cuisine, memory, weights, avoid,
                           {winner: rent_shock}, False)
        r1, r2 = _ranked(agent), _ranked(agent2)
        s1 = {a["postal_code"]: a for a in r1}
        s2 = {a["postal_code"]: a for a in r2}
        new_best = r2[0]["postal_code"]
        print()
        print("SENSITIVITY RESULT")
        print("-" * 70)
        print("  %s economics factor: %.1f -> %.1f (rent shock x%.2f)"
              % (winner, s1[winner]["factors"]["economics"],
                 s2[winner]["factors"]["economics"], rent_shock))
        print("  %s total: %.1f -> %.1f"
              % (winner, s1[winner]["total"], s2[winner]["total"]))
        if new_best == winner:
            print("  Recommendation UNCHANGED: %s still wins (margin over "
                  "runner-up %s: %.1f -> %.1f points)."
                  % (winner, r2[1]["postal_code"],
                     r1[0]["total"] - r1[1]["total"],
                     r2[0]["total"] - r2[1]["total"]))
        else:
            print("  Recommendation CHANGED: %s (%.1f) overtakes %s (%.1f)."
                  % (new_best, s2[new_best]["total"], winner,
                     s2[winner]["total"]))
        return new_best
    return agent.best


def main():
    banner()
    memory = seed_memory()
    print("MEMORY — seeded with %d past session(s):" % len(memory.past_queries))
    for q in memory.past_queries:
        print("  - '%s' (cuisine: %s, winner: %s)"
              % (q["query"], q["cuisine"], q["winner"]))
    print()
    turn("I want to open a Chinese restaurant in Phoenix — "
         "where exactly should I open it?",
         "Chinese", memory, DEFAULT_WEIGHTS, label="TURN 1")
    print()
    print()
    turn("Interesting. Now show me again, but this time I want to AVOID "
         "heavy competition — find me the quietest viable spot.",
         "Chinese", memory, DEFAULT_WEIGHTS, avoid_competition=True,
         label="TURN 2 (follow-up, memory reused)")
    print("=" * 70)
    print("DEMO COMPLETE — agent used a plan, 5 tools, memory, and a")
    print("synthesizer across 2 turns. Fully deterministic, fully offline.")
    print("=" * 70)


if __name__ == "__main__":
    main()
