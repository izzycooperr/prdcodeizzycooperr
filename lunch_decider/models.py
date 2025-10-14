from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict

@dataclass
class UserPrefs:
    name: str
    # HARD requirements
    max_distance_miles: Optional[float] = None
    allergies: Set[str] = field(default_factory=set)
    strict_budget_level: Optional[int] = None

    # SOFT preferences
    preferred_cuisines: Set[str] = field(default_factory=set)
    must_have_items_soft: Set[str] = field(default_factory=set)
    budget_flexible_level: Optional[int] = None

@dataclass
class Restaurant:
    name: str
    cuisines: Set[str]
    menu_items: Set[str]
    price_level: int
    distance_miles: float
    estimated_wait_min: int
    capacity: int
    allergens_present: Set[str]

    @staticmethod
    def from_dict(d: Dict) -> "Restaurant":
        return Restaurant(
            name=d["name"],
            cuisines=set(map(str.lower, d.get("cuisines", []))),
            menu_items=set(map(str.lower, d.get("menu_items", []))),
            price_level=int(d.get("price_level", 2)),
            distance_miles=float(d.get("distance_miles", 5.0)),
            estimated_wait_min=int(d.get("estimated_wait_min", 15)),
            capacity=int(d.get("capacity", 10)),
            allergens_present=set(map(str.lower, d.get("allergens_present", []))),
        )
