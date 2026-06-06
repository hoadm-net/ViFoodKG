"""
Bước 1.3: Lấy giá trị dinh dưỡng tham chiếu từ USDA FoodData Central

Mục đích: cung cấp bảng reference nutrient cho ~50 nguyên liệu thô phổ biến
trên nhãn thực phẩm đóng gói Việt Nam. Dùng để validate & normalize giá trị
dinh dưỡng của Ingredient nodes trong KG.

API: SR Legacy + Foundation Foods (stable, peer-reviewed data)
Output:
    data/processed/usda_nutrients.json
    data/processed/usda_nutrients.csv

Run:
    python src/collect/fetch_usda.py
"""

import csv
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Nutrients we care about (USDA nutrient IDs)
# ---------------------------------------------------------------------------
NUTRIENT_IDS = {
    1008: "energy_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carb_g",
    1079: "fiber_g",
    2000: "sugar_g",
    1093: "sodium_mg",
    1258: "fat_saturated_g",
}

# ---------------------------------------------------------------------------
# Target ingredients
# Map: canonical Vietnamese name → (English search query, preferred description hint)
# ---------------------------------------------------------------------------
INGREDIENTS: list[tuple[str, str, str]] = [
    # (name_vi,                search_query,                           hint substring — case-insensitive)
    # — Bột & tinh bột
    ("Bột mì",                 "wheat flour white all purpose",        "wheat flour, white, all-purpose"),
    ("Bột mì nguyên cám",      "wheat flour whole grain",              "whole-grain"),
    ("Bột gạo",                "rice flour white unenriched",          "rice flour, white"),
    ("Tinh bột ngô",           "cornstarch",                           "cornstarch"),
    ("Tinh bột sắn",           "tapioca pearl dry",                    "tapioca, pearl, dry"),
    ("Tinh bột khoai tây",     "cornstarch",                           "cornstarch"),         # proxy: SR Legacy lacks pure potato starch
    ("Tinh bột biến tính",     "cornstarch",                           "cornstarch"),         # proxy: corn starch
    ("Bột năng",               "cassava raw",                          "cassava, raw"),
    # — Dầu & chất béo
    ("Dầu cọ",                 "oil palm",                             "oil, palm"),
    ("Dầu đậu nành",           "oil soybean salad",                    "oil, soybean"),
    ("Dầu hướng dương",        "oil sunflower mid-oleic",              "sunflower"),
    ("Dầu dừa",                "oil coconut",                          "oil, coconut"),
    ("Dầu cọ nhân",            "oil palm kernel",                      "palm kernel"),
    ("Bơ thực vật",            "margarine vegetable",                  "margarine"),
    ("Bơ sữa",                 "butter without salt",                  "butter, without salt"),
    ("Shortening",             "shortening household composite",        "shortening, household, composite"),
    # — Đường & chất tạo ngọt
    ("Đường trắng",            "sugars granulated",                    "sugars, granulated"),
    ("Đường glucose (dextrose)","sugars granulated",                    "sugars, granulated"),  # proxy: same caloric profile
    ("Fructose",               "fructose",                             "fructose"),
    ("Maltose",                "sugars granulated",                    "sugars, granulated"),  # proxy
    ("Siro ngô",               "syrups corn light",                    "syrups, corn, light"),
    ("Mật ong",                "honey",                                "honey"),
    # — Sữa & sản phẩm sữa
    ("Sữa bột nguyên kem",     "milk dry whole",                       "milk, dry, whole"),
    ("Sữa bột gầy",            "milk dry nonfat calcium reduced",      "milk, nonfat, dry"),
    ("Sữa đặc có đường",       "milk condensed sweetened canned",      "milk, canned, condensed, sweetened"),
    ("Whey protein",           "whey protein isolate",                 "whey"),
    ("Bơ sữa (cream)",         "cream fluid heavy whipping",           "cream, fluid, heavy whipping"),
    # — Trứng & đạm
    ("Trứng gà",               "egg whole raw fresh",                  "egg, whole, raw, fresh"),
    ("Lòng trắng trứng",       "egg white raw fresh",                  "egg, white, raw, fresh"),
    ("Bột đậu nành",           "soy flour full-fat raw",               "soy flour, full-fat"),
    ("Protein đậu nành",       "soy protein isolate",                  "soy protein isolate"),
    ("Gluten lúa mì",          "vital wheat gluten",                   "vital wheat gluten"),
    # — Gia vị & phụ gia cơ bản
    ("Muối",                   "salt table",                           "salt, table"),
    ("Bột ngọt (MSG)",         "glutamate monosodium salt",            "monosodium glutamate"),  # not in SR Legacy
    ("Acid citric",            "leavening agents cream of tartar",     "cream of tartar"),  # best proxy
    ("Bột nở (baking powder)", "leavening baking powder low sodium",   "baking powder, low-sodium"),
    ("Bicarbonate natri",      "leavening baking soda",                "baking soda"),
    # — Nguyên liệu khác phổ biến trên nhãn VN
    ("Bột cacao",              "cocoa dry powder unsweetened",         "cocoa, dry powder, unsweetened"),
    ("Chocolate đen",          "chocolate dark 70-85% cacao",          "chocolate, dark"),
    ("Nước cốt dừa",           "coconut milk raw liquid",              "coconut milk, raw"),
    ("Nước mắm",               "sauce fish ready-to-serve",            "fish, ready-to-serve"),
    ("Tiêu đen",               "spices pepper black",                  "spices, pepper, black"),
    ("Tỏi bột",                "spices garlic powder",                 "spices, garlic powder"),
    ("Hành bột",               "spices onion powder",                  "spices, onion powder"),
    ("Ớt bột",                 "spices chili powder",                  "spices, chili powder"),
    ("Malt đại mạch",          "barley malt flour",                    "barley malt flour"),
    ("Lúa mì nảy mầm",        "wheat germ crude",                     "wheat germ, crude"),
    ("Yến mạch",               "cereals oats regular not fortified dry","cereals, oats, regular"),
    ("Đậu phộng",              "peanuts all types raw",                "peanuts, all types, raw"),
    ("Vừng / mè",              "seeds sesame whole dried",             "seeds, sesame seeds, whole, dried"),
    ("Hạt điều",               "cashew nuts raw",                      "nuts, cashew nuts, raw"),
]

# ---------------------------------------------------------------------------
# USDA API
# ---------------------------------------------------------------------------
FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
REQUEST_DELAY  = 0.4   # seconds between API calls


def _search(query: str, hint: str, api_key: str, client: httpx.Client) -> dict | None:
    """
    Search SR Legacy + Foundation, return best matching food dict or None.

    Matching priority:
    1. Description contains the full hint substring (exact)
    2. Description contains all query words (loose)
    3. None — do not fall back to unrelated results
    """
    query_words = set(query.lower().split())

    for data_type in ("SR Legacy", "Foundation"):
        r = client.get(
            FDC_SEARCH_URL,
            params={
                "query":    query,
                "dataType": data_type,
                "pageSize": 10,
                "api_key":  api_key,
            },
            timeout=20,
        )
        r.raise_for_status()
        foods = r.json().get("foods", [])
        if not foods:
            continue

        hint_lower = hint.lower()
        desc_lower_list = [f["description"].lower() for f in foods]

        # Pass 1: full hint match
        for food, desc in zip(foods, desc_lower_list):
            if hint_lower in desc:
                return food

        # Pass 2: at least 2 query words in description (avoids unrelated fallbacks)
        for food, desc in zip(foods, desc_lower_list):
            if sum(1 for w in query_words if w in desc) >= max(2, len(query_words) // 2):
                return food

    return None


def _extract_nutrients(food: dict) -> dict:
    """Pull the nutrients we care about from a food search result."""
    values = {name: None for name in NUTRIENT_IDS.values()}
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId")
        if nid in NUTRIENT_IDS:
            val = n.get("value")
            values[NUTRIENT_IDS[nid]] = round(float(val), 3) if val is not None else None
    return values


# ---------------------------------------------------------------------------
# Main fetch
# ---------------------------------------------------------------------------

def fetch_all(api_key: str) -> list[dict]:
    records: list[dict] = []

    with httpx.Client(
        headers={"User-Agent": "ViFoodKG-research/1.0 (hoadm.me@gmail.com)"},
    ) as client:
        for name_vi, query, hint in INGREDIENTS:
            print(f"  {name_vi:<25} → ", end="", flush=True)
            food = _search(query, hint, api_key, client)

            if food is None:
                print("NOT FOUND")
                records.append({
                    "name_vi":     name_vi,
                    "search_query": query,
                    "fdc_id":      None,
                    "description": None,
                    **{k: None for k in NUTRIENT_IDS.values()},
                })
                continue

            nutrients = _extract_nutrients(food)
            records.append({
                "name_vi":      name_vi,
                "search_query": query,
                "fdc_id":       food["fdcId"],
                "description":  food["description"],
                **nutrients,
            })
            kcal = nutrients.get("energy_kcal")
            print(f'{food["description"][:55]}  [{kcal} kcal]')

            time.sleep(REQUEST_DELAY)

    return records


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export(records: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "usda_nutrients.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\n[ok] JSON → {json_path}  ({len(records)} entries)")

    csv_path = out_dir / "usda_nutrients.csv"
    fieldnames = [
        "name_vi", "search_query", "fdc_id", "description",
        "energy_kcal", "protein_g", "fat_g", "carb_g",
        "fiber_g", "sugar_g", "sodium_mg", "fat_saturated_g",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"[ok] CSV  → {csv_path}")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(records: list[dict]) -> None:
    total   = len(records)
    found   = sum(1 for r in records if r["fdc_id"] is not None)
    has_kcal = sum(1 for r in records if r.get("energy_kcal") is not None)

    print(f"\n{'─'*42}")
    print(f"  Ingredients queried  : {total}")
    print(f"  Found in USDA        : {found}  ({found/total*100:.0f}%)")
    print(f"  Has energy (kcal)    : {has_kcal}")
    print(f"{'─'*42}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("USDA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("USDA_API_KEY not set in .env")

    root    = Path(__file__).resolve().parents[2]
    out_dir = root / "data/processed"

    print("=== Bước 1.3 — USDA FoodData Central ===\n")
    records = fetch_all(api_key)
    print_stats(records)
    export(records, out_dir)
