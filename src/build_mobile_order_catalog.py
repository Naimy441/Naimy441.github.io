#!/usr/bin/env python3
"""Build a lossless Mobile Order catalog with nutrition matches.

The Mobile Order export is the source of truth for menu structure.  This script
keeps every restaurant, section, item, option group, and option value in that
shape and only adds ``_nutrition_match`` annotations.  Nutrition matching is
deterministic when possible and uses Jev through Vercel AI Gateway for the
remaining ambiguous cases.

The script intentionally does not turn option values into top-level food
items.  They remain nested below their parent item exactly as Mobile Order
returned them.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MOBILE_DIR = ROOT / "mobile_order" / "menus"
DEFAULT_NUTRITION_FILE = ROOT / "outputs" / "nutri_menus.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "mobile_order_catalog.json"
DEFAULT_CACHE = ROOT / "outputs" / "mobile_order_catalog.jev-cache.json"
GATEWAY_EVALUATE_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
DEFAULT_MODEL = "typesafe-ai/jev"
ANNOTATION_KEY = "_nutrition_match"
NO_MATCH = "NO_MATCH"
CACHE_VERSION = 3
CACHE_SCOPE = "top_level_menu_items_only"


def load_env_file(path: Path) -> None:
    """Load only missing simple KEY=value entries from an ignored env file."""

    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = text.replace("saladalia", "saladelia")
    text = text.replace("j.b.'s", "jbs").replace("j.b.s", "jbs")
    text = text.replace("zweli's", "zwelis")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def tokens(value: Any) -> set[str]:
    return set(normalize_text(value).split())


def restaurant_key(value: Any) -> str:
    """Collapse known Mobile Order/NetNutrition naming differences."""

    normalized = normalize_text(value)
    # These are deliberate source-to-source mappings, not fuzzy guesses. The
    # Mobile Order feed has renamed or consolidated several venues since the
    # nutrition export was collected.
    if normalized in {"beyu blue", "beyu blue coffee"}:
        return "beyu_blue_coffee"
    if normalized == "cafe at duke law":
        return "bseisu_coffee_bar"
    if normalized in {"cafe", "cafe 300"}:
        return "cafe"
    if normalized in {"farmstead and sprout sandwiches", "the farmstead", "farmstead", "sprout"}:
        return "farmstead_sprout"
    if normalized in {"tandoor", "tandoor indian cuisine"}:
        return "tandoor_indian_cuisine"
    if normalized in {"trinity", "trinity cafe"}:
        return "trinity_cafe"
    if "saladelia" in normalized or "saladalia" in normalized:
        if "perkins" in normalized or "perk" in normalized:
            return "saladelia_perkins"
        if "sanford" in normalized:
            return "saladelia_sanford"
    if "sanford deli" in normalized:
        return "saladelia_sanford"
    if "ginger" in normalized and "soy" in normalized:
        return "ginger_soy"
    if "devil" in normalized and "krafthouse" in normalized:
        return "devils_krafthouse"
    if "pitchfork" in normalized:
        return "pitchfork"
    if "jbs" in normalized and ("roast" in normalized or "chop" in normalized):
        return "jbs_roast_chops"
    if "zweli" in normalized:
        return "zweli"
    if "freeman" in normalized:
        return "freeman"
    if normalized == "cafe" or normalized.startswith("cafe at "):
        return "cafe"
    return normalized


def item_names(record: dict[str, Any]) -> list[str]:
    """Return useful names without inventing or mutating source data."""

    names: list[str] = []
    for key in ("name", "qp_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip() and value not in names:
            names.append(value)
    return names


def compact_nutrition(nutrition: dict[str, Any], meal: dict[str, Any]) -> dict[str, Any]:
    """Provide the app-friendly shape while retaining the full raw nutrition."""

    return {
        "item": nutrition.get("item_name") or meal.get("name"),
        "restaurant": meal.get("_restaurant"),
        "category": meal.get("_category"),
        "servingSize": (nutrition.get("serving_info") or {}).get("serving_size"),
        "calories": nutrition.get("calories"),
        "facts": nutrition.get("nutrition_facts") or {},
        "secondary": nutrition.get("secondary_nutrients") or {},
        "ingredients": nutrition.get("ingredients"),
        "allergens": nutrition.get("allergens"),
    }


def nutrition_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Read either the full nutri_menus.json export or compact nutrition.json."""

    records: list[dict[str, Any]] = []
    if isinstance(data.get("restaurants"), list):
        for restaurant in data["restaurants"]:
            restaurant_name = restaurant.get("name") or ""
            for category in restaurant.get("categories") or []:
                for meal in category.get("meals") or []:
                    nutrition = meal.get("nutrition")
                    if not isinstance(nutrition, dict):
                        continue
                    enriched_meal = dict(meal)
                    enriched_meal["_restaurant"] = restaurant_name
                    enriched_meal["_category"] = category.get("name")
                    item_name = nutrition.get("item_name") or meal.get("name") or ""
                    records.append({
                        "item_name": item_name,
                        "restaurant": restaurant_name,
                        "category": category.get("name"),
                        "item_norm": normalize_text(item_name),
                        "restaurant_norm": restaurant_key(restaurant_name),
                        "source": "outputs/nutri_menus.json",
                        "nutrition": nutrition,
                        "compact": compact_nutrition(nutrition, enriched_meal),
                    })
    elif isinstance(data.get("byRestaurant"), dict):
        for restaurant_name, items in data["byRestaurant"].items():
            for item_key, nutrition in (items or {}).items():
                if not isinstance(nutrition, dict):
                    continue
                item_name = nutrition.get("item") or item_key
                records.append({
                    "item_name": item_name,
                    "restaurant": nutrition.get("restaurant") or restaurant_name,
                    "category": nutrition.get("category"),
                    "item_norm": normalize_text(item_name),
                    "restaurant_norm": restaurant_key(nutrition.get("restaurant") or restaurant_name),
                    "source": "dukeislam/data/nutrition.json",
                    "nutrition": nutrition,
                    "compact": nutrition,
                })
    else:
        raise ValueError("Nutrition input must contain either restaurants[] or byRestaurant")

    for index, record in enumerate(records):
        stable = "|".join([
            record["restaurant_norm"],
            record["item_norm"],
            normalize_text(record.get("category")),
            str(index),
        ])
        record["record_id"] = "nutrition_" + hashlib.sha1(stable.encode()).hexdigest()[:16]
    return records


def candidate_score(restaurant: str, name: str, record: dict[str, Any]) -> float:
    target_name = normalize_text(name)
    candidate_name = record["item_norm"]
    if not target_name or not candidate_name:
        return 0.0

    if target_name == candidate_name:
        name_score = 1.0
    else:
        target_tokens = set(target_name.split())
        candidate_tokens = set(candidate_name.split())
        overlap = len(target_tokens & candidate_tokens) / max(len(target_tokens | candidate_tokens), 1)
        sequence = difflib.SequenceMatcher(None, target_name, candidate_name).ratio()
        substring = 0.94 if target_name in candidate_name or candidate_name in target_name else 0.0
        name_score = max(overlap, sequence, substring)

    target_rest = restaurant_key(restaurant)
    candidate_rest = record["restaurant_norm"]
    if target_rest == candidate_rest:
        rest_score = 1.0
    else:
        target_tokens = tokens(target_rest)
        candidate_tokens = tokens(candidate_rest)
        overlap = len(target_tokens & candidate_tokens) / max(len(target_tokens | candidate_tokens), 1)
        rest_score = max(overlap, difflib.SequenceMatcher(None, target_rest, candidate_rest).ratio())

    return 0.72 * name_score + 0.28 * rest_score


class NutritionMatcher:
    def __init__(self, records: list[dict[str, Any]], max_candidates: int = 12) -> None:
        self.records = records
        self.max_candidates = max_candidates
        self.local_cache: dict[str, dict[str, Any] | None] = {}
        self.by_exact_name: dict[str, list[dict[str, Any]]] = {}
        self.by_token: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            self.by_exact_name.setdefault(record["item_norm"], []).append(record)
            for token in tokens(record["item_name"]):
                self.by_token.setdefault(token, []).append(record)

    def candidates(self, restaurant: str, name: str) -> list[dict[str, Any]]:
        name_norm = normalize_text(name)
        exact = self.by_exact_name.get(name_norm, [])
        pool: dict[str, dict[str, Any]] = {r["record_id"]: r for r in exact}
        for token in tokens(name):
            for record in self.by_token.get(token, []):
                pool[record["record_id"]] = record

        if not pool:
            pool = {r["record_id"]: r for r in self.records}

        ranked = sorted(
            ((candidate_score(restaurant, name, record), record) for record in pool.values()),
            key=lambda pair: (-pair[0], pair[1]["record_id"]),
        )
        return [{**record, "score": round(score, 4)} for score, record in ranked[: self.max_candidates]]

    def local_match(self, restaurant: str, names: Iterable[str]) -> dict[str, Any] | None:
        names = tuple(name for name in names if isinstance(name, str) and name.strip())
        cache_key_value = restaurant_key(restaurant) + "|" + "|".join(normalize_text(name) for name in names)
        if cache_key_value in self.local_cache:
            cached = self.local_cache[cache_key_value]
            return copy.deepcopy(cached) if cached is not None else None

        for name in names:
            exact_candidates = self.by_exact_name.get(normalize_text(name), [])
            same_restaurant_candidates = [
                candidate
                for candidate in exact_candidates
                if candidate["restaurant_norm"] == restaurant_key(restaurant)
            ]
            candidate = None
            method = "exact_restaurant"
            if same_restaurant_candidates:
                candidate = same_restaurant_candidates[0]
            elif len(exact_candidates) == 1:
                candidate = exact_candidates[0]
                method = "exact_global"
            if candidate is not None:
                result = self.annotation(candidate, method=method, probability=1.0, confidence=1.0)
                self.local_cache[cache_key_value] = result
                return copy.deepcopy(result)

        self.local_cache[cache_key_value] = None
        return None

    @staticmethod
    def annotation(
        candidate: dict[str, Any],
        *,
        method: str,
        probability: float | None,
        confidence: float | None,
        proposed: bool = False,
    ) -> dict[str, Any]:
        return {
            "status": "review" if proposed else "matched",
            "method": method,
            "probability": probability,
            "confidence": confidence,
            "record_id": candidate["record_id"],
            "matched_item": candidate["item_name"],
            "matched_restaurant": candidate["restaurant"],
            "matched_category": candidate.get("category"),
            "nutrition": candidate["nutrition"],
            "nutrition_compact": candidate["compact"],
        }


def annotation_without_match(
    *,
    method: str = "unmatched",
    candidates: list[dict[str, Any]] | None = None,
    selected: dict[str, Any] | None = None,
    probability: float | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "unmatched" if selected is None else "review",
        "method": method,
        "probability": probability,
        "confidence": confidence,
        "record_id": None,
        "matched_item": None,
        "matched_restaurant": None,
        "matched_category": None,
        "nutrition": None,
        "nutrition_compact": None,
    }
    if selected is not None:
        result["proposed_record_id"] = selected["record_id"]
        result["proposed_item"] = selected["item_name"]
        result["proposed_restaurant"] = selected["restaurant"]
        result["proposed_category"] = selected.get("category")
        result["proposed_nutrition"] = selected["nutrition"]
        result["proposed_nutrition_compact"] = selected["compact"]
    if candidates:
        result["candidates"] = [
            {
                "record_id": candidate["record_id"],
                "item": candidate["item_name"],
                "restaurant": candidate["restaurant"],
                "category": candidate.get("category"),
                "local_score": candidate.get("score"),
            }
            for candidate in candidates
        ]
    return result


def cache_key(restaurant: str, name: str, kind: str, candidates: list[dict[str, Any]]) -> str:
    value = {
        "restaurant": restaurant_key(restaurant),
        "name": normalize_text(name),
        "kind": kind,
        "candidates": [candidate["record_id"] for candidate in candidates],
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": CACHE_VERSION, "scope": CACHE_SCOPE, "matches": {}}
    try:
        data = read_json(path)
        if (
            isinstance(data, dict)
            and data.get("version") == CACHE_VERSION
            and data.get("scope") == CACHE_SCOPE
            and isinstance(data.get("matches"), dict)
        ):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": CACHE_VERSION, "scope": CACHE_SCOPE, "matches": {}}


def gateway_evaluate(
    state: dict[str, Any],
    questions: dict[str, Any],
    *,
    model: str,
    timeout: int = 90,
    retries: int = 3,
    zero_data_retention: bool = False,
) -> dict[str, Any]:
    api_key = os.environ.get("AI_GATEWAY_API_KEY")
    if not api_key:
        raise RuntimeError("AI_GATEWAY_API_KEY is not set; use --no-ai for an offline build")

    body: dict[str, Any] = {
        "model": model,
        "state": state,
        "questions": questions,
    }
    if zero_data_retention:
        body["providerOptions"] = {"gateway": {"zeroDataRetention": True}}
    for attempt in range(retries):
        try:
            response = requests.post(
                GATEWAY_EVALUATE_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"AI Gateway request failed: {exc}") from exc
            time.sleep(2**attempt)
            continue

        if response.ok:
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
                raise RuntimeError("AI Gateway returned no answers")
            return payload

        if response.status_code not in {408, 429, 500, 502, 503, 504} or attempt == retries - 1:
            detail = response.text[:500].replace("\n", " ")
            raise RuntimeError(f"AI Gateway returned HTTP {response.status_code}: {detail}")
        retry_after = response.headers.get("Retry-After")
        try:
            delay = max(float(retry_after or 0), 2**attempt)
        except ValueError:
            delay = 2**attempt
        time.sleep(min(delay, 30))
    raise RuntimeError("AI Gateway request failed")


def jev_matches(
    pending: list[dict[str, Any]],
    matcher: NutritionMatcher,
    cache: dict[str, Any],
    cache_path: Path,
    *,
    model: str,
    batch_size: int,
    min_probability: float,
    min_confidence: float,
    use_ai: bool,
    refresh_cache: bool,
    zero_data_retention: bool,
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    requests_to_make: list[dict[str, Any]] = []
    cache_matches = cache.setdefault("matches", {})

    for entry in pending:
        if use_ai:
            candidates = matcher.candidates(entry["restaurant"], entry["name"])
        else:
            candidates = []
        key = cache_key(entry["restaurant"], entry["name"], entry["kind"], candidates)
        entry["cache_key"] = key
        entry["candidates"] = candidates
        if not refresh_cache and key in cache_matches:
            resolved[entry["pending_key"]] = interpret_jev_answer(
                cache_matches[key], candidates, min_probability=min_probability, min_confidence=min_confidence
            )
        elif use_ai:
            if candidates and candidates[0]["score"] >= 0.55:
                requests_to_make.append(entry)
            else:
                resolved[entry["pending_key"]] = annotation_without_match(method="no_plausible_candidate")
        else:
            resolved[entry["pending_key"]] = annotation_without_match(method="not_run", candidates=candidates)

    if not requests_to_make:
        return resolved

    print(f"Jev matching: {len(requests_to_make)} unresolved top-level menu items in batches of {batch_size}")
    for offset in range(0, len(requests_to_make), batch_size):
        batch = requests_to_make[offset : offset + batch_size]
        questions: dict[str, Any] = {}
        state_items: list[dict[str, Any]] = []
        question_maps: dict[str, dict[str, Any]] = {}
        for index, entry in enumerate(batch):
            question_id = f"q{index}"
            candidate_map: dict[str, dict[str, Any]] = {NO_MATCH: {"record_id": NO_MATCH}}
            criteria: dict[str, str] = {
                NO_MATCH: "None of the listed nutrition records is the same food item; use this for a genuinely new or unrelated item."
            }
            for candidate_index, candidate in enumerate(entry["candidates"]):
                option = f"C{candidate_index}"
                candidate_map[option] = candidate
                criteria[option] = (
                    f"Food item '{candidate['item_name']}' from restaurant '{candidate['restaurant']}'"
                    + (f", category '{candidate['category']}'" if candidate.get("category") else "")
                )
            question_maps[question_id] = candidate_map
            state_items.append({
                "question_id": question_id,
                "kind": entry["kind"],
                "restaurant": entry["restaurant"],
                "food_item": entry["name"],
                "candidate_options": list(criteria),
            })
            questions[question_id] = {
                "type": "choice",
                "instructions": (
                    f"Match the {entry['kind']} named '{entry['name']}' at '{entry['restaurant']}' to an existing nutrition record. "
                    "Use restaurant and food name together. Choose NO_MATCH when no candidate is a plausible match. "
                    "Never choose a merely related ingredient or a different preparation."
                ),
                "criteria": criteria,
            }

        try:
            payload = gateway_evaluate(
                {"task": "match Mobile Order food names to nutrition records", "items": state_items},
                questions,
                model=model,
                zero_data_retention=zero_data_retention,
            )
            answers = payload["answers"]
            confidence_map = ((payload.get("providerMetadata") or {}).get("typesafe") or {}).get("confidence") or {}
            for entry, question_id in zip(batch, questions):
                answer = answers.get(question_id) or {"type": "choice", "choice": NO_MATCH, "probabilities": {}}
                answer = dict(answer)
                answer["confidence"] = confidence_map.get(question_id)
                cache_matches[entry["cache_key"]] = answer
                resolved[entry["pending_key"]] = interpret_jev_answer(
                    answer,
                    entry["candidates"],
                    min_probability=min_probability,
                    min_confidence=min_confidence,
                )
            write_json_atomic(cache_path, cache)
            print(f"  processed {min(offset + batch_size, len(requests_to_make))}/{len(requests_to_make)}")
        except RuntimeError as exc:
            print(f"  warning: {exc}; preserving unresolved records without guessing", file=sys.stderr)
            for entry in batch:
                resolved[entry["pending_key"]] = annotation_without_match(
                    method="jev_error", candidates=entry["candidates"]
                )
        time.sleep(0.1)

    return resolved


def interpret_jev_answer(
    answer: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    min_probability: float,
    min_confidence: float,
) -> dict[str, Any]:
    choice = answer.get("choice", NO_MATCH)
    probabilities = answer.get("probabilities") or {}
    probability = probabilities.get(choice)
    confidence = answer.get("confidence")
    candidate_map = {f"C{index}": candidate for index, candidate in enumerate(candidates)}
    selected = candidate_map.get(choice)
    if selected is not None and isinstance(probability, (int, float)) and probability >= min_probability:
        if confidence is None or confidence >= min_confidence:
            return NutritionMatcher.annotation(
                selected,
                method="jev",
                probability=float(probability),
                confidence=float(confidence) if confidence is not None else None,
            )
        return annotation_without_match(
            method="jev_review",
            candidates=candidates,
            selected=selected,
            probability=float(probability),
            confidence=float(confidence),
        )
    return annotation_without_match(
        method="jev_no_match" if choice == NO_MATCH else "jev_review",
        candidates=candidates,
        selected=selected,
        probability=float(probability) if isinstance(probability, (int, float)) else None,
        confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
    )


def enrich_value(
    value: dict[str, Any],
    restaurant: str,
    kind: str,
    matcher: NutritionMatcher,
    pending: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    names = item_names(value)
    local = matcher.local_match(restaurant, names)
    enriched = copy.deepcopy(value)
    if local is not None:
        enriched[ANNOTATION_KEY] = local
        return enriched
    # Option values are deliberately not sent to Jev as food items. Most are
    # ingredients/add-ons without a standalone NetNutrition record, and the
    # parent menu item is the food item users are selecting.
    enriched[ANNOTATION_KEY] = {
        "status": "nested_option_no_standalone_record" if names else "empty_name",
        "method": "exact_only_for_nested_option",
        "probability": None,
        "confidence": None,
        "record_id": None,
        "matched_item": None,
        "matched_restaurant": None,
        "matched_category": None,
        "nutrition": None,
        "nutrition_compact": None,
    }
    return enriched


def enrich_catalog(
    mobile_files: list[Path],
    matcher: NutritionMatcher,
    *,
    nutrition_source: Path,
    model: str,
    cache_path: Path,
    batch_size: int,
    min_probability: float,
    min_confidence: float,
    use_ai: bool,
    refresh_cache: bool,
    zero_data_retention: bool,
    limit: int | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    pending: dict[str, dict[str, Any]] = {}
    restaurants: list[dict[str, Any]] = []
    source_counts = {"restaurants": 0, "sections": 0, "items": 0, "option_groups": 0, "option_values": 0}

    for file_path in mobile_files:
        menu = read_json(file_path)
        restaurant_name = menu.get("restaurant") or file_path.stem
        restaurant_out = {key: copy.deepcopy(value) for key, value in menu.items() if key != "sections"}
        sections_out: list[dict[str, Any]] = []
        source_counts["restaurants"] += 1
        for section_index, section in enumerate(menu.get("sections") or []):
            section_out = {key: copy.deepcopy(value) for key, value in section.items() if key != "items"}
            items_out: list[dict[str, Any]] = []
            source_counts["sections"] += 1
            for item_index, item in enumerate(section.get("items") or []):
                if limit is not None and source_counts["items"] >= limit:
                    break
                item_out = {key: copy.deepcopy(value) for key, value in item.items() if key != "options"}
                item_out["catalog_item_id"] = (
                    f"{file_path.name}:{section.get('section_id', section_index)}:"
                    f"{item.get('itemid', item_index)}:{item_index}"
                )
                source_counts["items"] += 1
                item_out[ANNOTATION_KEY] = {"status": "pending", "method": "local_or_jev"}
                item_names_for_match = item_names(item)
                local = matcher.local_match(restaurant_name, item_names_for_match)
                if local is not None:
                    item_out[ANNOTATION_KEY] = local
                elif item_names_for_match:
                    name = item_names_for_match[0]
                    key = "|".join([restaurant_key(restaurant_name), normalize_text(name), "menu_item"])
                    pending.setdefault(
                        key,
                        {
                            "pending_key": key,
                            "restaurant": restaurant_name,
                            "name": name,
                            "kind": "menu item",
                        },
                    )

                options_out: list[dict[str, Any]] = []
                for option_index, option in enumerate(item.get("options") or []):
                    option_out = {key: copy.deepcopy(value) for key, value in option.items() if key != "values"}
                    source_counts["option_groups"] += 1
                    values_out: list[dict[str, Any]] = []
                    for value in option.get("values") or []:
                        source_counts["option_values"] += 1
                        values_out.append(enrich_value(value, restaurant_name, "option value", matcher, pending))
                    option_out["values"] = values_out
                    options_out.append(option_out)
                item_out["options"] = options_out
                items_out.append(item_out)
            section_out["items"] = items_out
            sections_out.append(section_out)
            if limit is not None and source_counts["items"] >= limit:
                break
        restaurant_out["sections"] = sections_out
        restaurants.append(restaurant_out)
        if limit is not None and source_counts["items"] >= limit:
            break

    cache = load_cache(cache_path)
    pending_results = jev_matches(
        list(pending.values()),
        matcher,
        cache,
        cache_path,
        model=model,
        batch_size=batch_size,
        min_probability=min_probability,
        min_confidence=min_confidence,
        use_ai=use_ai,
        refresh_cache=refresh_cache,
        zero_data_retention=zero_data_retention,
    )
    write_json_atomic(cache_path, cache)

    def replace_pending(value: Any) -> Any:
        if isinstance(value, list):
            return [replace_pending(item) for item in value]
        if not isinstance(value, dict):
            return value
        updated = {key: replace_pending(item) for key, item in value.items()}
        annotation = updated.get(ANNOTATION_KEY)
        if isinstance(annotation, dict) and annotation.get("status") == "pending":
            # The item's own name is not stored in the placeholder to keep the
            # source-shaped object uncluttered, so replacement is performed by
            # the explicit traversal below instead.
            return updated
        return updated

    def apply_annotations(menu: dict[str, Any]) -> None:
        restaurant_name = menu.get("restaurant") or ""
        for section in menu.get("sections") or []:
            for item in section.get("items") or []:
                item_annotation = item.get(ANNOTATION_KEY)
                if isinstance(item_annotation, dict) and item_annotation.get("status") == "pending":
                    names = item_names(item)
                    key = "|".join([restaurant_key(restaurant_name), normalize_text(names[0]), "menu_item"])
                    item[ANNOTATION_KEY] = pending_results.get(key, annotation_without_match(method="missing_result"))
                for option in item.get("options") or []:
                    for value in option.get("values") or []:
                        annotation = value.get(ANNOTATION_KEY)
                        if isinstance(annotation, dict) and annotation.get("status") == "pending":
                            names = item_names(value)
                            key = "|".join([restaurant_key(restaurant_name), normalize_text(names[0]), "option value"])
                            value[ANNOTATION_KEY] = pending_results.get(
                                key, annotation_without_match(method="missing_result")
                            )

    # Work from the already-built restaurant-shaped data and apply the cached
    # or Jev-derived annotations without changing any Mobile Order fields.
    for restaurant in restaurants:
        apply_annotations(restaurant)

    stats = dict(source_counts)
    stats["pending_unique_names"] = len(pending)
    stats["matched"] = 0
    stats["review"] = 0
    stats["unmatched"] = 0
    for restaurant in restaurants:
        for section in restaurant.get("sections") or []:
            for item in section.get("items") or []:
                annotations = [item.get(ANNOTATION_KEY)]
                annotations.extend(
                    value.get(ANNOTATION_KEY)
                    for option in item.get("options") or []
                    for value in option.get("values") or []
                )
                for annotation in annotations:
                    status = (annotation or {}).get("status", "unmatched")
                    stats[status] = stats.get(status, 0) + 1

    catalog = {
        "schema_version": "mobile_order_nutrition.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "mobile_order": "mobile_order/menus/*.json",
            "nutrition": str(nutrition_source.relative_to(ROOT)) if nutrition_source.is_relative_to(ROOT) else str(nutrition_source),
            "ai_gateway_evaluation_endpoint": GATEWAY_EVALUATE_URL,
            "ai_gateway_model": model,
        },
        "matching": {
            "local_exact_and_fuzzy_first": True,
            "jev_used_for_unresolved": use_ai,
            "jev_min_probability": min_probability,
            "jev_min_confidence": min_confidence,
            "unmatched_records_are_retained": True,
            "options_remain_nested": True,
        },
        "stats": stats,
        "restaurants": restaurants,
    }
    return catalog, stats


def validate_lossless(catalog: dict[str, Any], mobile_files: list[Path]) -> None:
    """Check that no source-shaped Mobile Order fields were removed."""

    if len(catalog.get("restaurants") or []) != len(mobile_files):
        raise ValueError("Lossless validation failed: restaurant count changed")

    def strip_annotations(value: Any) -> Any:
        if isinstance(value, list):
            return [strip_annotations(item) for item in value]
        if isinstance(value, dict):
            return {
                key: strip_annotations(item)
                for key, item in value.items()
                if key not in {ANNOTATION_KEY, "catalog_item_id"}
            }
        return value

    for file_path, output_restaurant in zip(mobile_files, catalog["restaurants"]):
        source = read_json(file_path)
        source_without_sections = {key: value for key, value in source.items() if key != "sections"}
        output_without_sections = {key: value for key, value in output_restaurant.items() if key != "sections"}
        if strip_annotations(source_without_sections) != strip_annotations(output_without_sections):
            raise ValueError(f"Lossless validation failed for restaurant metadata: {file_path.name}")
        for source_section, output_section in zip(source.get("sections") or [], output_restaurant.get("sections") or []):
            source_items = source_section.get("items") or []
            output_items = output_section.get("items") or []
            if len(source_items) != len(output_items):
                raise ValueError(f"Lossless validation failed for item count: {file_path.name}")
            for source_item, output_item in zip(source_items, output_items):
                source_copy = {key: value for key, value in source_item.items() if key != "options"}
                output_copy = {key: value for key, value in output_item.items() if key not in {"options", ANNOTATION_KEY, "catalog_item_id"}}
                if source_copy != output_copy:
                    raise ValueError(f"Lossless validation failed for item fields: {file_path.name}")
                for source_option, output_option in zip(source_item.get("options") or [], output_item.get("options") or []):
                    source_values = source_option.get("values") or []
                    output_values = output_option.get("values") or []
                    output_option_copy = {key: value for key, value in output_option.items() if key != "values"}
                    if source_option != output_option_copy | {"values": source_values}:
                        raise ValueError(f"Lossless validation failed for option group: {file_path.name}")
                    for source_value, output_value in zip(source_values, output_values):
                        output_value_copy = {key: value for key, value in output_value.items() if key != ANNOTATION_KEY}
                        if source_value != output_value_copy:
                            raise ValueError(f"Lossless validation failed for option value: {file_path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobile-dir", type=Path, default=DEFAULT_MOBILE_DIR)
    parser.add_argument("--nutrition-file", type=Path, default=DEFAULT_NUTRITION_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--min-probability", type=float, default=0.70)
    parser.add_argument("--min-confidence", type=float, default=0.45)
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--no-ai", action="store_true", help="Build locally without making Gateway requests")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument(
        "--zero-data-retention",
        action="store_true",
        help="Request Gateway ZDR (requires a plan that supports request-level ZDR)",
    )
    parser.add_argument("--limit", type=int, help="Process only this many menu items for a smoke test")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(ROOT / ".env.local")
    mobile_files = sorted(args.mobile_dir.glob("*.json"))
    if not mobile_files:
        raise SystemExit(f"No Mobile Order menu JSON files found in {args.mobile_dir}")
    if not args.nutrition_file.exists():
        raise SystemExit(f"Nutrition file not found: {args.nutrition_file}")

    nutrition = nutrition_records(read_json(args.nutrition_file))
    matcher = NutritionMatcher(nutrition, max_candidates=args.max_candidates)
    catalog, stats = enrich_catalog(
        mobile_files,
        matcher,
        nutrition_source=args.nutrition_file,
        model=args.model,
        cache_path=args.cache,
        batch_size=args.batch_size,
        min_probability=args.min_probability,
        min_confidence=args.min_confidence,
        use_ai=not args.no_ai,
        refresh_cache=args.refresh_cache,
        zero_data_retention=args.zero_data_retention,
        limit=args.limit,
    )
    if args.limit is None:
        validate_lossless(catalog, mobile_files)
    else:
        print("Skipped full lossless validation because --limit was used")
    write_json_atomic(args.output, catalog)
    print(f"Wrote {args.output}")
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
