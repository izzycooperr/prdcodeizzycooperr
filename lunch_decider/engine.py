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
    """
    load_restaurants function
    Summary:
    Loads the list of restaurants from a json file to be used

    Input:
    path (str) - A string that represents the filepath to the  
    
    Output:

    List[Restaurant] - A list of Restaurant objects from the json file
    that the path leads to
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Restaurant.from_dict(r) for r in raw]

def violates_hard_constraints(r: Restaurant, users: List[UserPrefs]) -> Tuple[bool, str]:
    """
    violates_hard_constraints function
    Summary:
    Checks to see if restaurant or user-determined constraints are met or
    violated 
    Takes into account restaurant capacity, user-to-restaurant distance, user allergies,
    and user budget

    Input:

    r (Restaurant) - The data of the restaurant that is being considered

    users (List[UserPrefs]) - A list of user preferences to be compared against
    the qualities of the selected restaurant

    Output:
    
    Tuple[bool, str] - A tuple consisting of a bool that is true if user or restaurant
    constraints are not maintained, and a string detailing which constraint was violated

    Note: If multiple constraints are violated, only the first one in the list of 'if'
    statements is logged. Could be refactored 
    """
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
    """
    score_restaurant function
    Summary:
    Calculates the compatibility score of the selected restaurant relative to the 
    preferences of the users

    Input:

    r (Restaurant) - The data of the restaurant being scored

    users (List[UserPrefs]) - The preferences of each user based on their input

    Output:

    Tuple[float, Dict[str, float] - A tuple containing a float representing compatibility
    between a restaurant and a user, and a dictionary with entries containing the compatibility
    categories and the score within said category
    """
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

def pick_best(restaurants: List[Restaurant], users: List[UserPrefs]) -> Tuple[list, list]:
    """
    pick_best function

    Summary: Select the best restaurant based on the calculated compatibility
    score, excluding the incompatible restaurants

    Note: More or less just combines violates_hard_constraints and 
    score_restaurant. Can probably be refactored

    Input:

    restaurants (List[Restaurant]) - The list of restauraunts and their data

    users: (List[UserPrefs]) - The list of user-input preferences
    
    Output:

    Tuple[list, list] - Returns a tuple of 2 lists, the first being a list of 
    Restaurant objects that have a possible compatibility, and the second being
    Restaurants that do not have compatibility, or do not meet constraints
    """
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
    """
    run_cli function
    Summary:
    The function called by main to initiate the program

    Input:
    N/A
    
    Output:
    N/A
    """
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
                break
            break
        print_recommendation(ranked, rejected)
        again = input("Not interested? Want to try a different restaurant? (y/n): ").lower()
        if again == "y":
            excluded.add(ranked[0][0].name)
            continue
        break

def ask_value(prompt, min_v=1, max_v=4, optional=False):
    """
    ask_value function
    Summary: 
    Returns an int value from user input.

    Input:
    
    prompt (str) - The text prompting the user to input a value

    optional (bool) - Determines if a prompt is optional

    Output:
    
    float | None - Can return an int value based on user input,
    or nothing if optional and given no input
    """
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
    """
    ask_set function
    Summary: Returns a set of strings from user input, split by commas

    Input:

    prompt (str) - A string prompting user for input

    Output:

    set[] - A set of strings split from user input
    """
    s = input(prompt).strip().lower()
    return set([x.strip() for x in s.split(",") if x.strip()])

def collect_users() -> list:
    """
    collect_users function
    Summary:
    Collects user input for use

    Note: All input is optional. Should probably require SOME input
    
    Input:

    Varies; determied by users; All optional

    name (str) - Name of user
    dist (float) - Distance user is willing to drive
    allergies (set) - Allergies of the user
    mode (str) - A user-inputted string of either "strict" or "flex"
    strict (float) - An integer of 1-4 representing "price level"
    cuisines (set) - A set of meal types ("seafood", "vegan", etc.)
    must (set) - Specific meal items that the user must have

    Output:
    users (list) - A list of UserPrefs, which are made up of user-input values representing 
    the meal preferences of each user
    """
    users = []
    n = ask_value("How many people (2–6)? ", 2, 6)
    for i in range(n):
        print(f"\nPerson {i+1}:")
        name = input("  Name: ").strip() or f"Person{i+1}"
        dist = ask_value("  Max distance (mi, Enter to skip): ", 0, 30, True)
        allergies = ask_set("  Allergies (comma separated, Enter for none): ")
        mode = input("  Is your budget strict or flex? ").strip().lower()
        strict = flex = None
        if mode == "strict":
            strict = ask_value("    Strict budget (1–4), 1 being cheap, 4 being expensive: ")
        elif mode == "flex":
            flex = ask_value("    Preferred budget (1–4), 1 being cheap, 4 being expensive: ")
        cuisines = ask_set("  Preferred cuisines (Enter to skip): ")
        must = ask_set("  Must-have items (Enter to skip): ")
        users.append(UserPrefs(name, dist, allergies, strict, cuisines, must, flex))
    return users

def adjust_preferences(users: List[UserPrefs]):
    print("No matches. Try increasing distance or relaxing budgets.")
