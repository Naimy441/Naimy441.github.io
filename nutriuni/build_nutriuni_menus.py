#!/usr/bin/env python3
"""Build Nutriuni's menu data: Mobile Order structure + NetNutrition nutrition.

Mobile Order is the source of truth for *what is on the menu*: restaurants,
sections, dishes, prices, and the option groups a diner picks from (sides,
sauces, proteins, toppings...). NetNutrition is the source of nutrition labels.
This script links the two, one restaurant at a time:

* each Mobile Order dish is matched to a NetNutrition item (its "base" label);
* each option value is matched to a NetNutrition item too, so choosing
  "Fries" or "Add Smoked Bacon" adds that component's nutrition;
* combos and build-your-own dishes are composed from their components;
* "No X" options subtract X when X is a known component of the dish.

Matching is deterministic: names are normalized (punctuation, plurals, common
abbreviations, typos such as Baigan/Baingan), weighted by how distinctive each
word is within that restaurant, and checked from both sides so "Chicken" never
silently matches "Chicken Alfredo Pasta". Low-confidence pairs are left
unmatched, because a missing label is better than a wrong one; the app lets the
user enter nutrition or log without it. ``nutriuni/nutriuni_overrides.json`` holds
hand-reviewed corrections for the cases a string matcher cannot know.

Outputs ``nutriuni/menus/`` (index.json, restaurants/*.json, icons/) and a
review report at ``nutriuni/menus/match_report.md``.

    python nutriuni/build_nutriuni_menus.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from update_nutrition_library import serving_grams, slug as library_slug

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MOBILE_DIR = ROOT / "outputs" / "mobile_order"
DEFAULT_LIBRARY_DIR = ROOT / "nutriuni" / "nutrition_library"
DEFAULT_OVERRIDES = ROOT / "nutriuni" / "nutriuni_overrides.json"
DEFAULT_OUTPUT_DIR = ROOT / "nutriuni" / "menus"
DEFAULT_HOURS_INDEX = ROOT / "outputs" / "restaurants" / "index.json"

SCHEMA_VERSION = 1
NUTRIENTS = (
    "calories", "protein", "carbs", "fat", "fiber", "sugar", "sodium",
    "saturated_fat", "trans_fat", "cholesterol", "added_sugar",
    "calcium", "iron", "potassium",
)

# NetNutrition marks labels with icons: allergens the dish contains, and
# Vegetarian / Vegan / Halal. Published as stable lowercase codes. An empty
# list only means "nothing marked", never "free of": units that publish no
# icons of a kind are flagged allergen_info / diet_info: false on the restaurant.
ALLERGEN_CODES = {
    "milk": "milk", "egg": "egg", "eggs": "egg", "wheat": "wheat", "gluten": "gluten",
    "soy": "soy", "peanut": "peanut", "peanuts": "peanut", "tree nut": "tree_nut",
    "tree nuts": "tree_nut", "fish": "fish", "shellfish": "shellfish", "sesame": "sesame",
}
DIET_CODES = {"vegetarian": "vegetarian", "vegan": "vegan"}


def icon_codes(icons: Iterable[str]) -> tuple[list[str], list[str]]:
    contains: set[str] = set()
    diet: set[str] = set()
    for icon in icons or []:
        key = " ".join(str(icon).lower().split())
        if key in ALLERGEN_CODES:
            contains.add(ALLERGEN_CODES[key])
        elif key in DIET_CODES:
            diet.add(DIET_CODES[key])
    if "vegan" in diet:
        diet.add("vegetarian")
    return sorted(contains), sorted(diet)


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "the", "with", "w", "of", "on", "in", "or", "to", "for",
    "our", "your", "fresh", "house", "made", "homemade", "style", "portion",
    "pc", "pcs", "piece", "pieces", "ct", "count", "oz", "serving", "side",
    "contains", "coconut", "choice", "option", "options", "v", "ve", "vg", "gf",
    "cup", "regular", "classic", "signature", "famous", "new", "item", "special",
}
# Tokens rewritten before comparison. Values may be several words.
SYNONYMS = {
    "mac": "macaroni", "bbq": "barbecue", "chz": "cheese", "veg": "vegetable",
    "veggie": "vegetable", "veggies": "vegetable", "fries": "fry", "dosai": "dosa",
    "1000": "thousand", "parm": "parmesan", "choc": "chocolate", "tenders": "tender",
    "blta": "blt a", "philly": "philadelphia", "sammy": "sandwich", "sandwhich": "sandwich",
    "tomatoes": "tomato", "potatoes": "potato", "chilli": "chili", "chile": "chili",
    "yoghurt": "yogurt", "ceaser": "caesar", "iceburg": "iceberg", "tarter": "tartar",
    "pattie": "patty", "patties": "patty", "pepperoni": "pepperoni", "jalapenos": "jalapeno",
    "omlette": "omelet", "omelette": "omelet", "doughnut": "donut", "grilled": "grill",
    "griled": "grill", "housemade": "house made", "n": "and", "barbeque": "barbecue",
    "mixed": "mix", "lge": "large", "lg": "large", "reg": "regular", "sm": "small", "med": "medium",
}
ADD_PREFIX = re.compile(r"^(?:add(?:\s+on)?|extra|side\s+of|side|with|plus|top\s+with)\s+", re.I)
REMOVE_PREFIX = re.compile(r"^(?:no|hold(?:\s+the)?|without|remove|minus)\s+", re.I)
SUB_PREFIX = re.compile(r"^(?:sub(?:stitute)?|swap|replace|change\s+to|make\s+it|switch\s+to)\b\s*(?:for\s+|with\s+|to\s+)?", re.I)
NOOP_VALUE = re.compile(
    r"^(?:no\s+changes?|none|no\s+thanks|plain|as\s+is|regular|standard|no\s+(?:side|sauce|protein|dressing|extra|add\s*ons?|cheese\s+change|change\b.*))$"
    r"|\bon\s+(?:the\s+)?side\b|\blight\b|\beasy\b|\bwell\s+done\b|\btoasted\b|\bcut\s+in\s+half\b|\bnot\s+toasted\b",
    re.I,
)
SIZE_VALUE = re.compile(
    r"^(?:small|medium|large|regular|kids?|mini|half|full|whole|single|double|triple|bowl|cup|pint|quart|"
    r"\d+(?:\.\d+)?\s*(?:oz|ounce|in|inch|\"|pc|piece)s?)$",
    re.I,
)
# Words a NetNutrition component name may add without changing what it is:
# option "Ranch" is the label "Buttermilk Ranch Dressing", "Mushrooms" is
# "Sauteed Mushroom". Dish words (salad, burger, pizza...) are never forgiven.
FORM_WORDS = {
    "sauce", "dressing", "slice", "sliced", "topping", "crumble", "tidbit", "spread", "glaze",
    "sauteed", "grill", "roasted", "diced", "shredded", "chopped", "steamed", "cut", "fried",
    "buttermilk", "creamy", "blend", "mix", "leaf", "lettuce", "breast", "filet", "strip",
    "baby", "whole", "plain", "natural", "seasoned", "cheese",
}
# Descriptors either name may carry without changing the dish
# ("Onion Rings" = "Battered Onion Rings", "Seasoned Diced Potato" = "Diced Potato").
QUALITY_WORDS = {
    "seasoned", "creamy", "plain", "natural", "homestyle", "battered", "traditional",
    "classic", "original", "signature", "famous", "ultimate", "large", "small", "medium",
    "quarter", "half",
}
# A label that names a protein the dish doesn't is a different dish
# ("Nachos" is not "Chicken Cheese Nachos").
PROTEIN_WORDS = {
    "chicken", "beef", "steak", "shrimp", "pork", "turkey", "bacon", "salmon", "tuna", "fish",
    "tofu", "lamb", "sausage", "ham", "egg", "brisket", "meatball", "pepperoni", "mahi", "crab",
}
# Descriptors that never change what a dish is, for dish-level matching.
DISH_FORM_WORDS = {
    "sliced", "diced", "shredded", "chopped", "sauteed", "roasted", "steamed", "cut",
    "seasoned", "creamy", "plain", "natural", "house", "made", "breast", "filet", "fillet",
}
# A "Sandwiches" section explains "Panini", "Pita", "Wrap"... on the label.
SANDWICH_WORDS = {"sandwich", "panini", "pita", "wrap", "melt", "sub", "hoagie", "focaccia", "ciabatta"}
SIZE_HINT = re.compile(r"\b(\d+(?:\.\d+)?)\s*oz\b|\b(quarter|half|small|large|lge|lg|regular|reg|medium)\b", re.I)
# Words ignored when comparing a dish with its NetNutrition variants, and the
# tags assumed when no option says otherwise (plain "Latte" = whole milk, hot).
VARIANT_FREE = {"milk", "hot", "drink", "beverage"}
DEFAULT_TAGS = {"whole", "regular", "original"}
# Cup sizes are read from the label's serving ("Small (340g)") and are a soft
# preference: the right milk with the wrong size beats the wrong milk.
SIZE_TAGS = ("small", "medium", "large", "regular")
COMPOSED_NAME = re.compile(
    r"\b(?:build|custom|create|your\s+own|byo|combo|meal\s+deal|pick|choose|choice|slices?)\b", re.I
)
NON_COMPONENT_GROUP = re.compile(r"\b(?:size|temp|temperature|drink|beverage|utensil|napkin|instruction|cook)\b", re.I)


def ascii_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return text.replace("&", " and ").replace("+", " and ")


def stem(token: str) -> str:
    if token in SYNONYMS:
        return SYNONYMS[token]
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "oes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def clean_name(value: str | None) -> str:
    """Strip POS noise: 'ILF - Stinger', 'Wings (6)', 'Harvest (V)', trailing '*'."""

    text = ascii_text(value)
    text = re.sub(r"^[A-Z]{2,4}\s+-\s+", "", text)  # register prefixes such as "GOT - "
    text = re.sub(r"\((?:[^)]*)\)", " ", text)
    text = re.sub(r"\bcontains\s+\w+\b", " ", text, flags=re.I)
    return " ".join(text.replace("*", " ").split())


def tokens(value: str | None) -> list[str]:
    text = re.sub(r"(\d)\s*%", r"\1pct", clean_name(value).lower())
    words = re.findall(r"[a-z0-9]+", text)
    if len(words) > 1 and words[0].isdigit():
        words = words[1:]  # leading count: "2 Eggs", "3 Sides Platter"
    out: list[str] = []
    for word in words:
        for part in stem(word).split():
            part = stem(part)
            if part not in STOPWORDS:
                out.append(part)
    return out


def slug(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ascii_text(value).lower()).strip("-") or "item"


def similar(a: str, b: str) -> float:
    """Token similarity tolerant of small spelling differences."""

    if a == b:
        return 1.0
    if len(a) < 4 or len(b) < 4 or a[0] != b[0] or abs(len(a) - len(b)) > 2:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio if ratio >= 0.8 else 0.0


# ---------------------------------------------------------------------------
# Nutrition library
# ---------------------------------------------------------------------------


@dataclass
class Food:
    id: str
    name: str
    category: str | None
    serving_size: str | None
    nutrition: dict[str, float]
    halal: bool
    last_seen: str
    unit: str
    contains: list[str] = field(default_factory=list)
    diet: list[str] = field(default_factory=list)
    ingredients: str | None = None
    tokens: list[str] = field(default_factory=list)
    category_tokens: set[str] = field(default_factory=set)

    def public(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "serving_size": self.serving_size,
            **self.nutrition,
            "halal": self.halal,
            **({"contains": self.contains} if self.contains else {}),
            **({"diet": self.diet} if self.diet else {}),
            **({"ingredients": self.ingredients} if self.ingredients else {}),
            # Month precision is enough to warn about old labels and keeps the
            # published files from changing every day the label is re-seen.
            "last_seen": month_of(self.last_seen),
        }


def month_of(day: str | None) -> str | None:
    return f"{day[:7]}-01" if day and len(day) >= 7 else day


def load_unit_foods(library_dir: Path, unit: str) -> list[Food]:
    path = library_dir / f"{library_slug(unit)}.json"
    if not path.exists():
        return []
    library = json.loads(path.read_text(encoding="utf-8"))
    foods = []
    for key, entry in library.get("items", {}).items():
        if not entry.get("valid"):
            continue
        nutrition = {"calories": entry["calories"]}
        for nutrient in NUTRIENTS[1:]:
            value = (entry.get("nutrients") or {}).get(nutrient)
            if value is not None:
                nutrition[nutrient] = value
        contains, diet = icon_codes(entry.get("allergens") or [])
        foods.append(Food(
            id=hashlib.sha1(f"{unit}|{key}".encode()).hexdigest()[:10],
            name=entry["name"],
            category=entry.get("category"),
            serving_size=entry.get("serving_size"),
            nutrition=nutrition,
            halal=bool(entry.get("halal")),
            last_seen=entry.get("last_seen", ""),
            unit=unit,
            contains=contains,
            diet=diet,
            ingredients=entry.get("ingredients"),
            tokens=tokens(entry["name"]),
            category_tokens=set(tokens(entry.get("category"))),
        ))
    return foods


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


@dataclass
class Match:
    food: Food
    score: float
    cover_query: float
    cover_food: float
    method: str


class Matcher:
    """Weighted token matcher over one restaurant's NetNutrition foods."""

    def __init__(self, foods: list[Food], restaurant_words: set[str] = frozenset()):
        self.foods = foods
        self.restaurant_words = set(restaurant_words)
        df: dict[str, int] = {}
        for food in foods:
            for token in set(food.tokens):
                df[token] = df.get(token, 0) + 1
        self.n = max(len(foods), 1)
        self.df = df
        self.by_exact: dict[str, list[Food]] = {}
        for food in foods:
            self.by_exact.setdefault(" ".join(sorted(food.tokens)), []).append(food)

    def weight(self, token: str) -> float:
        return math.log(1 + self.n / self.df.get(token, 0.5))

    def _overlap(self, query: list[str], target: list[str]) -> tuple[float, set[int]]:
        """Weighted overlap of query tokens found in target; returns used target indexes."""

        used: set[int] = set()
        total = 0.0
        for token in query:
            best, best_index = 0.0, -1
            for index, candidate in enumerate(target):
                if index in used:
                    continue
                score = similar(token, candidate)
                if score > best:
                    best, best_index = score, index
            if best_index >= 0:
                used.add(best_index)
                total += best * self.weight(token)
        return total, used

    def score(
        self, query: list[str], context: set[str], food: Food, explain: set[str],
        context_explain: set[str], optional: set[str] | None = None, dish: bool = False,
    ) -> Match | None:
        if not query or not food.tokens:
            return None
        matched, used = self._overlap(query, food.tokens)
        if matched == 0:
            return None
        optional = optional or set()
        query_weight = sum(
            self.weight(t) for t in query
            if t not in optional or any(similar(t, f) for f in food.tokens)
        )
        cover_query = matched / query_weight
        # Food words not in the query are forgiven when the dish/section/option
        # group explains them ("Buffalo Chicken" in a "Pizza" section matches
        # "Buffalo Chicken Pizza").
        extra = [t for i, t in enumerate(food.tokens) if i not in used]
        unexplained = [t for t in extra if t not in explain and not any(similar(t, c) for c in context_explain)]
        if dish and any(t in PROTEIN_WORDS for t in unexplained):
            return None
        food_weight = sum(self.weight(t) for t in food.tokens)
        cover_food = 1 - sum(self.weight(t) for t in unexplained) / food_weight
        context_bonus = 0.0
        if context and food.category_tokens:
            hits = sum(1 for t in food.category_tokens if any(similar(t, c) for c in context))
            context_bonus = 0.08 * hits / len(food.category_tokens)
        score = 0.55 * cover_query + 0.45 * cover_food + context_bonus
        return Match(food, score, cover_query, cover_food, "fuzzy")

    def best(self, name: str, context: Iterable[str] = (), *, strict: bool) -> tuple[Match | None, list[Match]]:
        query = tokens(name)
        context_tokens = {t for c in context for t in tokens(c)} - set(query)
        # Dishes: the section name, the restaurant's own name and descriptors
        # explain extra words ("Pizza" section -> "Buffalo Chicken Pizza").
        # Option values: only form words do.
        if strict:
            if context_tokens & SANDWICH_WORDS:
                context_tokens |= SANDWICH_WORDS
            explain = DISH_FORM_WORDS | QUALITY_WORDS | self.restaurant_words
            context_explain, optional = context_tokens, QUALITY_WORDS | self.restaurant_words
        else:
            explain, context_explain, optional = FORM_WORDS, set(), set()
        exact = self.by_exact.get(" ".join(sorted(t for t in query if t not in optional)))
        candidates = [
            m for f in self.foods
            if (m := self.score(query, context_tokens, f, explain, context_explain, optional, dish=strict))
        ]
        candidates.sort(key=lambda m: (m.score, m.food.last_seen), reverse=True)
        if exact:
            # Identical names: let context pick between variants (e.g. a
            # "Fried Shrimp" side vs. a taco "Fried Shrimp" filling).
            ranked = [m for m in candidates if m.food in exact]
            top = ranked[0]
            food = pick_serving(name, exact, top.food) if strict else top.food
            if food is None:
                return None, candidates[:5]
            return Match(food, 1.0 + top.score, 1.0, 1.0, "exact"), candidates[:5]
        if not candidates:
            return None, []
        top = candidates[0]
        runner = next((m for m in candidates[1:] if not same_food(m.food, top.food)), None)
        margin = top.score - (runner.score if runner else 0)
        if strict:
            ok = top.cover_query >= 0.8 and top.cover_food >= 0.75 and top.score >= 0.8 and margin >= 0.06
        else:
            ok = top.cover_query >= 0.88 and top.cover_food >= 0.99 and margin >= 0.04
        if ok and strict:
            siblings = [f for f in self.foods if same_food(f, top.food)]
            food = pick_serving(name, siblings, top.food)
            if food is None:
                return None, candidates[:5]
            top = Match(food, top.score, top.cover_query, top.cover_food, top.method)
        return (top if ok else None), candidates[:5]


    def variants(self, name: str, context: Iterable[str], vocabulary: set[str]) -> list[tuple[Food, list[str]]]:
        """NetNutrition labels that are this dish plus option words.

        "Latte" with options Oat Milk / Iced finds "Latte Whole Milk",
        "Latte Oat Milk", "Iced Latte Oat Milk"...; each comes back with the
        option words it needs ("oat", "iced") so picking options picks the label.
        """

        query = tokens(name)
        if not query:
            return []
        free = VARIANT_FREE | {t for c in context for t in tokens(c)}
        sized = bool(vocabulary & set(SIZE_TAGS))
        family: dict[tuple[str, ...], Food] = {}
        for food in sorted(self.foods, key=lambda f: f.last_seen, reverse=True):
            matched, used = self._overlap(query, food.tokens)
            if len(used) < len(query) or matched < sum(self.weight(t) for t in query) * 0.9:
                continue
            extra = [t for i, t in enumerate(food.tokens) if i not in used and t not in free]
            if all(t in vocabulary or t in DEFAULT_TAGS for t in extra):
                need = set(extra)
                size = re.match(r"\s*(small|medium|large|regular)\b", (food.serving_size or "").lower())
                if sized and size:
                    need.add(size.group(1))
                family.setdefault(tuple(sorted(need)), food)
        return [(food, list(need)) for need, food in family.items()]


def pick_serving(name: str, siblings: list[Food], chosen: Food) -> Food | None:
    """Use size words in a dish name ("Prime Rib 8oz", "Mango Mojo Large")
    to choose between same-named labels with different servings. Returns None
    for a "Large" dish when NetNutrition has no label bigger than the smallest,
    since that label would understate it."""

    # "3 PC Fried Chicken": only a label whose serving states that count will do.
    count = re.match(r"^\s*(\d+)\s*(?:pc|pcs|piece|pieces)?\b", name, re.I)
    if count and int(count.group(1)) > 1:
        wanted = re.compile(rf"\b{count.group(1)}\s*(?:pc|pcs|piece|pieces|ct)\b", re.I)
        return next((f for f in siblings if wanted.search(f.serving_size or "")), None)
    hint = SIZE_HINT.search(name)
    if not hint:
        return chosen
    sized = [f for f in siblings if serving_grams(f.serving_size) is not None]
    if hint.group(2) and stem(hint.group(2).lower()) == "large":
        grams = sorted({serving_grams(f.serving_size) for f in sized})
        if len(grams) < 2 or grams[-1] < grams[0] * 1.2:
            return None
    if len(siblings) < 2:
        return chosen
    if hint.group(1):
        wanted = re.compile(rf"\b{re.escape(hint.group(1))}\s*oz\b", re.I)
        return next((f for f in siblings if wanted.search(f.serving_size or "")), chosen)
    word = stem(hint.group(2).lower())
    named = [f for f in siblings if re.search(rf"\b{word}\b", f.serving_size or "", re.I)]
    if named:
        return named[0]
    if word in ("small", "regular") and sized:
        return min(sized, key=lambda f: serving_grams(f.serving_size))
    if word == "large" and sized:
        return max(sized, key=lambda f: serving_grams(f.serving_size))
    return chosen


def pick_variant(variants: list[dict[str, Any]], selected: set[str]) -> dict[str, Any] | None:
    """Mirror of resolveBase() in the app: chosen options must explain every
    non-size tag (defaults fill gaps); matching milk/temperature outweighs size."""

    allowed = selected | DEFAULT_TAGS
    best, best_score = None, None
    for variant in variants:
        need = set(variant["need"])
        sizes = need & set(SIZE_TAGS)
        if not (need - sizes) <= allowed:
            continue
        score = (
            3 * len((need - sizes) & selected) + len(sizes & selected) - len(sizes - allowed),
            -len(need),
        )
        if best_score is None or score > best_score:
            best, best_score = variant, score
    return best


def same_food(a: Food, b: Food) -> bool:
    return a.tokens == b.tokens


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------


class Overrides:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.restaurants: dict[str, dict[str, Any]] = data.get("restaurants", {})
        self.netnutrition_only: list[str] = data.get("netnutrition_only_restaurants", [])

    def for_restaurant(self, name: str) -> dict[str, Any]:
        return self.restaurants.get(name, {})


def lookup_food(foods: list[Food], ref: str) -> Food | None:
    """Resolve 'Name', 'Name @ Category' or 'Name # serving text'."""

    ref, _, serving = (part.strip() for part in ref.partition("#"))
    name, _, category = (part.strip() for part in ref.partition("@"))
    key = " ".join(tokens(name))
    hits = [f for f in foods if " ".join(f.tokens) == key or f.name.lower() == name.lower()]
    if category:
        hits = [f for f in hits if (f.category or "").lower() == category.lower()]
    if serving:
        hits = [f for f in hits if serving.lower() in (f.serving_size or "").lower()]
    hits.sort(key=lambda f: f.last_seen, reverse=True)
    return hits[0] if hits else None


def item_override(rules: dict[str, Any], section: str, name: str) -> dict[str, Any]:
    items = rules.get("items", {})
    for key in (f"{section} > {name}", name):
        if key in items:
            return items[key]
    for pattern in rules.get("item_patterns", []):
        if re.search(pattern["match"], name, flags=re.I):
            return pattern
    return {}


def value_override(rules: dict[str, Any], item: str, group: str, value: str) -> dict[str, Any] | None:
    values = rules.get("values", {})
    for key in (f"{item} > {group} > {value}", f"{group} > {value}", value):
        if key in values:
            return values[key]
    return None


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


@dataclass
class Stats:
    items: int = 0
    with_nutrition: int = 0
    base_matched: int = 0
    composed: int = 0
    values: int = 0
    values_component: int = 0
    values_matched: int = 0


class RestaurantBuilder:
    def __init__(self, name: str, foods: list[Food], rules: dict[str, Any]):
        self.name = name
        self.foods = foods
        self.rules = rules
        words = {t for n in [name, *rules.get("netnutrition_units", [])] for t in tokens(n)}
        self.matcher = Matcher(foods, words)
        self.used: dict[str, Food] = {}
        self.stats = Stats()
        self.report: list[str] = []
        self.value_log: dict[str, str] = {}
        self.item_ids: set[str] = set()

    def use(self, food: Food | None) -> str | None:
        if food is None:
            return None
        self.used[food.id] = food
        return food.id

    def resolve_ref(self, ref: str | None, where: str) -> Food | None:
        if ref is None:
            return None
        food = lookup_food(self.foods, ref)
        if food is None:
            self.report.append(f"  - ⚠️ override `{ref}` for {where} not found in NetNutrition library")
        return food

    def classify_value(self, item: str, section: str, group: dict[str, Any], value: dict[str, Any], components: list[Food]) -> dict[str, Any]:
        name = value["name"]
        out: dict[str, Any] = {"name": name}
        if value.get("price"):
            out["price"] = value["price"]
        if value.get("is_default"):
            out["default"] = True
        if value.get("max_quantity") and group.get("allow_quantity"):
            out["max_quantity"] = value["max_quantity"]

        override = value_override(self.rules, item, group["name"], name)
        if override is not None:
            kind = override.get("kind", "add")
            food = self.resolve_ref(override.get("food"), f"`{group['name']} > {name}`")
            out["kind"] = kind
            self.stats.values_component += 1
            if food:
                out["food"] = self.use(food)
                if override.get("quantity"):
                    out["quantity"] = override["quantity"]
                self.stats.values_matched += 1
                self.value_log[name] = f"**{food.name}** ({food.serving_size}, {food.nutrition['calories']} kcal) [manual]"
            return out

        cleaned = clean_name(name).strip()
        if NOOP_VALUE.search(cleaned):
            out["kind"] = "none"
            return out
        removal = REMOVE_PREFIX.match(cleaned)
        if removal:
            target = cleaned[removal.end():]
            out["kind"] = "remove"
            # Only separately listed components can be taken away: "No Naan"
            # removes a combo's naan, but "No Chicken" never removes the whole
            # "Chicken Alfredo Pasta" label.
            target_tokens = set(tokens(target))
            for component in components:
                if target_tokens and target_tokens <= set(component.tokens):
                    out["food"] = self.use(component)
                    self.stats.values_matched += 1
                    break
            return out
        if SUB_PREFIX.match(cleaned):
            out["kind"] = "sub"
            return out
        if SIZE_VALUE.match(cleaned):
            out["kind"] = "size"
            return out

        quantity = 1
        target = ADD_PREFIX.sub("", cleaned)
        count = re.match(r"^(\d)\s+(.+)$", target)
        if count and 1 < int(count.group(1)) <= 6:
            quantity, target = int(count.group(1)), count.group(2)
        out["kind"] = "add"
        if NON_COMPONENT_GROUP.search(group["name"]):
            return out
        self.stats.values_component += 1
        match, _ = self.matcher.best(target, [group["name"]], strict=False)
        if match:
            out["food"] = self.use(match.food)
            if quantity > 1:
                out["quantity"] = quantity
            self.stats.values_matched += 1
            self.value_log[name] = (
                f"{match.food.name} ({match.food.serving_size}, {match.food.nutrition['calories']} kcal) "
                f"[{match.method} {match.score:.2f}]"
            )
        else:
            self.value_log.setdefault(name, "—")
        return out

    def build_item(self, section: str, item: dict[str, Any]) -> dict[str, Any]:
        name = item["name"]
        override = item_override(self.rules, section, name)
        item_id = f"{slug(section)}/{slug(name)}"
        suffix = 2
        while item_id in self.item_ids:
            item_id = f"{slug(section)}/{slug(name)}-{suffix}"
            suffix += 1
        self.item_ids.add(item_id)
        out: dict[str, Any] = {"id": item_id, "name": name}
        description = " ".join((item.get("description") or "").replace("�", " ").split())
        if description and description.lower() != name.lower() and not description.startswith("GC "):
            out["description"] = description
        if item.get("price") is not None:
            out["price"] = item["price"]

        base: Food | None = None
        method = None
        unmatched_note = None
        if "food" in override:
            base = self.resolve_ref(override["food"], f"item `{name}`")
            method = "manual" if base else "manual-none"
        else:
            match, candidates = self.matcher.best(name, [section], strict=True)
            if match:
                base, method = match.food, f"{match.method} {match.score:.2f}"
            elif candidates and candidates[0].score >= 0.55:
                c = candidates[0]
                unmatched_note = f"- ❔ `{name}` unmatched (closest: {c.food.name} {c.score:.2f})"
        components = [f for ref in override.get("components", []) if (f := self.resolve_ref(ref, f"item `{name}`"))]

        groups = []
        for group in item.get("options") or []:
            values = [v for v in group.get("values") or [] if not v.get("is_hidden") and v.get("name")]
            if not values:
                continue
            built_values = [self.classify_value(name, section, group, v, components) for v in values]
            self.stats.values += len(built_values)
            built = {"name": clean_name(group["name"]) or group["name"], "min": group.get("minimum") or 0}
            maximum = group.get("maximum")
            if maximum is not None and maximum < len(values):
                built["max"] = maximum
            if group.get("allow_quantity"):
                built["allow_quantity"] = True
            built["values"] = built_values
            groups.append(built)

        variants: list[dict[str, Any]] = []
        if "food" not in override:
            value_tags = {
                id(v): set(tokens(v["name"])) | set(re.findall(r"\b(small|medium|large|regular)\b", v["name"].lower()))
                for g in groups for v in g["values"] if v["kind"] not in ("remove", "none")
            }
            vocabulary = set().union(*value_tags.values()) if value_tags else set()
            family = self.matcher.variants(name, [section], vocabulary)
            if len(family) >= 2 or (family and base is None):
                needed = {t for _, need in family for t in need}
                variants = [{"food": self.use(food), "need": need} for food, need in family]
                for g in groups:
                    for v in g["values"]:
                        tags = sorted(value_tags.get(id(v), set()) & needed)
                        if tags:
                            v["tags"] = tags
                            v["kind"] = "variant"
                            v.pop("food", None)
                defaults = {t for g in groups for v in g["values"] if v.get("default") for t in v.get("tags", [])}
                chosen = pick_variant(variants, defaults)
                base = self.used[chosen["food"]] if chosen else base
                method = method or "variant"
                self.report.append(
                    f"- `{name}` variants: " + "; ".join(f"{self.used[x['food']].name} ⇐ {x['need'] or '[]'}" for x in variants)
                )

        if unmatched_note and base is None:
            self.report.append(unmatched_note)
        composed = bool(override.get("composed"))
        if base is None and not override.get("composed") is False:
            component_groups = [
                g for g in groups
                if sum(1 for v in g["values"] if v.get("food") and v["kind"] == "add") >= max(1, len(g["values"]) // 2)
            ]
            if component_groups and (components or COMPOSED_NAME.search(name)):
                composed = True

        if base:
            out["base"] = self.use(base)
            out["match"] = method
            if override.get("quantity"):
                out["base_quantity"] = override["quantity"]
            if base.halal:
                out["halal"] = True
            self.stats.base_matched += 1
            self.report.append(f"- `{name}` → **{base.name}** ({base.serving_size}, {base.nutrition['calories']} kcal) [{method}]")
        if variants:
            out["variants"] = variants
        if components:
            out["components"] = [self.use(c) for c in components]
            self.report.append(f"- `{name}` + components: {', '.join(c.name for c in components)}")
        if composed and not base:
            out["composed"] = True
            self.stats.composed += 1
            if not components:
                self.report.append(f"- `{name}` composed from its options")
        has_nutrition = bool(base or components or composed or variants)
        # The app shows options to compute nutrition, so keep groups that move
        # the numbers (plus required choices, for fidelity to the real order).
        groups = [
            g for g in groups
            if g["min"] >= 1 or any(v.get("food") or v.get("tags") for v in g["values"])
        ] if has_nutrition else []
        if groups:
            out["options"] = groups
        if has_nutrition:
            self.stats.with_nutrition += 1
        return out

    def build_mobile(self, menu: dict[str, Any]) -> list[dict[str, Any]]:
        sections = []
        skip = {slug(s) for s in self.rules.get("skip_sections", [])} | {"delivery"}
        for section in menu.get("sections", []):
            if section.get("is_hidden") or slug(section["name"]) in skip:
                continue
            items = [i for i in section.get("items") or [] if not i.get("is_hidden")]
            if not items:
                continue
            self.report.append(f"\n**{section['name']}**")
            built = [self.build_item(section["name"], item) for item in items]
            self.stats.items += len(built)
            sections.append({"name": section["name"], "items": built})
        return sections

    def build_netnutrition_only(self) -> list[dict[str, Any]]:
        by_category: dict[str, list[Food]] = {}
        seen: set[tuple[str, ...]] = set()
        for food in sorted(self.foods, key=lambda f: f.last_seen, reverse=True):
            key = tuple(food.tokens)
            if key in seen:
                continue
            seen.add(key)
            by_category.setdefault(food.category or "Menu", []).append(food)
        sections = []
        for category in sorted(by_category):
            items = []
            for food in sorted(by_category[category], key=lambda f: f.name):
                item = {"id": f"{slug(category)}/{slug(food.name)}", "name": food.name, "base": self.use(food), "match": "source"}
                if food.halal:
                    item["halal"] = True
                items.append(item)
            sections.append({"name": category, "items": items})
            self.stats.items += len(items)
            self.stats.with_nutrition += len(items)
            self.stats.base_matched += len(items)
        return sections


def weekly_hours(entry: dict[str, Any]) -> dict[str, list[list[str]]]:
    out = {}
    for day, windows in (entry.get("hours") or {}).items():
        spans = sorted({(w["open"], w["close"]) for w in windows.get("takeout") or [] if w.get("open") and w.get("close")})
        out[day] = [list(s) for s in spans]
    return out


def write_json(path: Path, payload: Any) -> str:
    """Write compact JSON and return a hash of the exact bytes written.

    The Cloud Function that publishes to Firestore re-hashes the bytes it
    downloads, so a file from a different commit than the index is rejected."""

    data = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return content_hash(data)


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:20]


def build(args: argparse.Namespace) -> int:
    overrides = Overrides(args.overrides)
    mobile_index = json.loads((args.mobile_dir / "restaurants.json").read_text(encoding="utf-8"))
    hours_text: dict[str, str] = {}
    if args.hours_index.exists():
        for name, info in json.loads(args.hours_index.read_text(encoding="utf-8")).get("restaurants", {}).items():
            hours_text[name] = info.get("hours", "")

    out_dir: Path = args.output_dir
    staging = out_dir.with_name(out_dir.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "restaurants").mkdir(parents=True)
    (staging / "icons").mkdir()

    index_rows = []
    report = ["# Nutriuni menu match report\n"]
    totals = Stats()

    jobs: list[tuple[str, dict[str, Any] | None]] = [(r["restaurant"], r) for r in mobile_index["restaurants"]]
    jobs += [(name, None) for name in overrides.netnutrition_only]

    for name, entry in jobs:
        rules = overrides.for_restaurant(name)
        units = rules.get("netnutrition_units", [] if entry else [name])
        excluded = {" ".join(tokens(name)) for name in rules.get("exclude_foods", [])}
        foods = [
            food for unit in units for food in load_unit_foods(args.library_dir, unit)
            if " ".join(food.tokens) not in excluded
        ]
        builder = RestaurantBuilder(name, foods, rules)
        display_name = rules.get("display_name", " ".join(name.split()))
        rid = slug(display_name)

        if entry:
            menu = json.loads((args.mobile_dir / entry["file"]).read_text(encoding="utf-8"))
            sections = builder.build_mobile(menu)
            source = "mobile_order"
        else:
            sections = builder.build_netnutrition_only()
            source = "netnutrition"
        if not sections:
            continue

        stats = builder.stats
        last_seen = month_of(max((f.last_seen for f in builder.used.values()), default=None))
        restaurant: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "id": rid,
            "name": display_name,
            "source": source,
            "nutrition_sources": units if foods else [],
            "nutrition_last_seen": last_seen,
            "stats": {"items": stats.items, "with_nutrition": stats.with_nutrition},
            "sections": sections,
            "foods": {fid: food.public() for fid, food in sorted(builder.used.items())},
            # Whether this kitchen marks allergens / diets on its labels at all,
            # so the app can tell "nothing marked" from "not published".
            "allergen_info": any(food.contains for food in foods),
            "diet_info": any(food.diet for food in foods),
        }
        icon = icon_hash = None
        if entry:
            restaurant["location_id"] = entry.get("location_id")
            restaurant["hours"] = weekly_hours(entry)
            restaurant["menu_updated_at"] = entry.get("menu_last_updated")
            icon_name = Path(entry.get("icon_image_url") or "").name
            icon_path = args.mobile_dir / "images" / icon_name
            if icon_name and icon_path.exists():
                icon = f"{rid}.jpg"
                shutil.copyfile(icon_path, staging / "icons" / icon)
                icon_hash = content_hash(icon_path.read_bytes())
        else:
            restaurant["hours_text"] = next((hours_text[u] for u in units if hours_text.get(u)), "")
        file_hash = write_json(staging / "restaurants" / f"{rid}.json", restaurant)

        coverage = stats.with_nutrition / stats.items if stats.items else 0
        index_rows.append({
            "id": rid,
            "name": display_name,
            "file": f"{rid}.json",
            "hash": file_hash,
            "source": source,
            "icon": icon,
            "icon_hash": icon_hash,
            "items": stats.items,
            "with_nutrition": stats.with_nutrition,
            "nutrition_last_seen": last_seen,
            **({"hours": restaurant["hours"]} if entry else {"hours_text": restaurant["hours_text"]}),
        })
        for attr in vars(totals):
            setattr(totals, attr, getattr(totals, attr) + getattr(stats, attr))
        value_rate = f"{stats.values_matched}/{stats.values_component}" if stats.values_component else "-"
        report.append(
            f"\n## {display_name}\n\nSource: {source}; NetNutrition units: {', '.join(units) or 'none'} "
            f"({len(foods)} labels). Items with nutrition: {stats.with_nutrition}/{stats.items} ({coverage:.0%}); "
            f"base labels {stats.base_matched}, composed {stats.composed}; option components matched {value_rate}.\n"
        )
        report.extend(builder.report)
        if builder.value_log:
            report.append("\n**Option values**\n")
            report.extend(f"- `{v}` → {t}" for v, t in sorted(builder.value_log.items(), key=lambda kv: kv[0].lower()))

    index_rows.sort(key=lambda r: r["name"].lower())
    # generated_at is the time the published data last changed, so a rebuild
    # with identical results produces byte-identical files (no git churn, no
    # Firestore writes, no app downloads).
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    previous_index = out_dir / "index.json"
    if previous_index.exists():
        previous = json.loads(previous_index.read_text(encoding="utf-8"))
        if previous.get("restaurants") == index_rows and previous.get("schema_version") == SCHEMA_VERSION:
            generated_at = previous["generated_at"]
    write_json(staging / "index.json", {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "restaurants": index_rows,
    })
    report[0] = f"# Nutriuni menu match report\n\nData version {generated_at}.\n"
    summary = (
        f"\n---\nTotals: {totals.with_nutrition}/{totals.items} items with nutrition "
        f"({totals.base_matched} base labels, {totals.composed} composed); "
        f"{totals.values_matched}/{totals.values_component} option components matched.\n"
    )
    report.insert(1, summary)
    (staging / "match_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    staging.rename(out_dir)
    print(summary.strip().replace("---\n", ""))
    print(f"Wrote {len(index_rows)} restaurants to {out_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mobile-dir", type=Path, default=DEFAULT_MOBILE_DIR)
    parser.add_argument("--library-dir", type=Path, default=DEFAULT_LIBRARY_DIR)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--hours-index", type=Path, default=DEFAULT_HOURS_INDEX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return build(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
