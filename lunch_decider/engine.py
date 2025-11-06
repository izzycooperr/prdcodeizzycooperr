import json, os, random
from typing import List, Tuple, Dict, Set
from .models import UserPrefs, Restaurant

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "restaurants.json")

# ----- Scoring Weights -----
W_CUISINE = 2.0
W_MENU_ITEM = 3.0
W_PRICE = 2.0
W_WAIT = 1.0
W_DISTANCE = 1.0

def load_restaurants(path: str = DATA_PATH) -> List[Restaurant]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Restaurant.from_dict(r) for r in raw]

def violates_hard_constraints(r: Restaurant, users: List[UserPrefs]) -> Tuple[bool, str]:
    group_size = len(users)
    if r.capacity < group_size:
        return True, f"insufficient capacity ({r.capacity} < group size {group_size})"
    for u in users:
        if u.max_distance_miles and r.distance_miles > u.max_distance_miles:
            return True, f"distance {r.distance_miles} exceeds {u.name}'s max {u.max_distance_miles}"
        if u.allergies & r.allergens_present:
            return True, f"allergen risk for {u.name}: {', '.join(sorted(u.allergies & r.allergens_present))}"
        if u.strict_budget_level and r.price_level > u.strict_budget_level:
            return True, f"price {r.price_level} exceeds {u.name}'s strict budget {u.strict_budget_level}"
    return False, ""

def score_restaurant(r: Restaurant, users: List[UserPrefs]) -> Tuple[float, Dict[str, float]]:
    score = 0.0
    breakdown = {"cuisine": 0, "menu": 0, "price": 0, "wait": 0, "distance": 0}

    for u in users:
        if u.preferred_cuisines and r.cuisines & u.preferred_cuisines:
            breakdown["cuisine"] += W_CUISINE
        if u.must_have_items_soft and r.menu_items & u.must_have_items_soft:
            breakdown["menu"] += W_MENU_ITEM
        if u.budget_flexible_level and not u.strict_budget_level:
            delta = r.price_level - u.budget_flexible_level
            if delta <= 0:
                breakdown["price"] += W_PRICE
            elif delta == 1:
                breakdown["price"] += W_PRICE * 0.25

    if r.estimated_wait_min <= 10:
        breakdown["wait"] += W_WAIT
    elif r.estimated_wait_min <= 20:
        breakdown["wait"] += W_WAIT * 0.6
    elif r.estimated_wait_min <= 30:
        breakdown["wait"] += W_WAIT * 0.3

    if r.distance_miles <= 2:
        breakdown["distance"] += W_DISTANCE
    elif r.distance_miles <= 5:
        breakdown["distance"] += W_DISTANCE * 0.5
    elif r.distance_miles <= 10:
        breakdown["distance"] += W_DISTANCE * 0.25

    score = sum(breakdown.values())
    return score, breakdown

def pick_best(restaurants: List[Restaurant], users: List[UserPrefs]):
    ranked, rejected = [], []
    for r in restaurants:
        bad, reason = violates_hard_constraints(r, users)
        if bad:
            rejected.append((r, reason))
        else:
            total, breakdown = score_restaurant(r, users)
            ranked.append((r, total, breakdown))
    ranked.sort(key=lambda t: t[1], reverse=True)
    return ranked, rejected

def print_recommendation(ranked, rejected):
    if not ranked:
        print("No results found. Would you like to change preferences?")
        for r, reason in rejected[:5]:
            print(f" - {r.name}: {reason}")
        return
    top_score = ranked[0][1]
    best = [t for t in ranked if abs(t[1] - top_score) < 1e-6]
    choice = random.choice(best)
    r, total, breakdown = choice
    print("\nRecommended restaurant:")
    print(f"  {r.name} — {r.distance_miles} mi, wait {r.estimated_wait_min} min, price {r.price_level}/4")
    for k, v in breakdown.items():
        print(f"  {k}: {v:.1f}")
    print(f"Total score: {total:.1f}")

def run_cli():
    restaurants = load_restaurants()
    users = collect_users()
    excluded = set()

    while True:
        candidates = [r for r in restaurants if r.name not in excluded]
        ranked, rejected = pick_best(candidates, users)
        if not ranked:
            adjust = input("Adjust preferences? (y/n): ").lower()
            if adjust == "y":
                adjust_preferences(users)
                continue
            break
        print_recommendation(ranked, rejected)
        again = input("Exclude and re-suggest? (y/n): ").lower()
        if again == "y":
            excluded.add(ranked[0][0].name)
            continue
        elif again == "n" and ranked:
            show_menu = input("Alright! Glad to have found you a restaurant! Would you like to see the menu? (y/n): ").lower()
            if show_menu == "y":
                print("Menu Items:")
                for mi in ranked[0][0].menu_items:
                    print(f"{mi}")
        break

def ask_float(prompt, optional=False):
    while True:
        s = input(prompt).strip()
        if optional and not s:
            return None
        try:
            v = float(s)
            if v > 30:
                print("Distance too large. Please choose a number between 1–30 miles.")
                continue
            return v
        except ValueError:
            print("Please enter a valid number for distance.")

def ask_int(prompt, min_v=1, max_v=4, optional=False):
    while True:
        s = input(prompt).strip()
        if optional and not s:
            return None
        try:
            v = int(s)
            if not (min_v <= v <= max_v):
                print(f"Please enter {min_v}–{max_v}.")
                continue
            return v
        except ValueError:
            print("Please enter a valid number.")

def ask_set(prompt):
    s = input(prompt).strip().lower()
    return set([x.strip() for x in s.split(",") if x.strip()])

def collect_users():
    users = []
    n = ask_int("How many people (2–6)? ", 2, 6)
    for i in range(n):
        print(f"\nPerson {i+1}:")
        name = input("  Name: ").strip() or f"Person{i+1}"
        dist = ask_float("  Max distance (mi, Enter to skip): ", True)
        allergies = ask_set("  Allergies (comma separated, Enter for none): ")
        mode = input("  Budget strict or flex? ").strip().lower()
        strict = flex = None
        if mode == "strict":
            strict = ask_int("    Strict budget (1–4): ")
        elif mode == "flex":
            flex = ask_int("    Preferred budget (1–4): ")
        cuisines = ask_set("  Preferred cuisines (Enter to skip): ")
        must = ask_set("  Must-have items (Enter to skip): ")
        users.append(UserPrefs(name, dist, allergies, strict, cuisines, must, flex))
    return users

def adjust_preferences(users: List[UserPrefs]):
    print("No matches. Try increasing distance or relaxing budgets.")
