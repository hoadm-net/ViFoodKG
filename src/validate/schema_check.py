"""
Schema Validation — kiểm tra 186 sản phẩm OFF Vietnam trước khi scale Bước 2.

Checks:
  C1  — CONSTRAINT_1: 5 mandatory nutrients present
  C2  — CONSTRAINT_2: sugar present when product contains sweeteners
  C3  — CONSTRAINT_3: fat_saturated present when product is fried/chip
  CAT — Category assignability: OFF tags → ViFoodKG taxonomy
  ING — Ingredient parsability heuristic
  BRD — Brand completeness

Output:
  data/processed/schema_validation_report.json
  (also printed to stdout)

Run:
    python src/validate/schema_check.py
"""

import json
import re
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Category mapping: OFF tag fragment → ViFoodKG category ID
# Priority order matters — more specific first
# ---------------------------------------------------------------------------
CATEGORY_MAP: list[tuple[str, str]] = [
    # CANDY
    ("chocolate",              "CANDY.CHOCOLATE"),
    ("bonbon",                 "CANDY.CHOCOLATE"),
    ("hard-candy",             "CANDY.HARD"),
    ("hard-candies",           "CANDY.HARD"),
    ("lollipop",               "CANDY.HARD"),
    ("chewing-gum",            "CANDY.GUM"),
    ("bubble-gum",             "CANDY.GUM"),
    ("gummies",                "CANDY.SOFT"),
    ("jelly-candy",            "CANDY.SOFT"),
    ("soft-candy",             "CANDY.SOFT"),
    ("candy",                  "CANDY.SOFT"),
    ("confectionery",          "CANDY.SOFT"),
    ("confectioneries",        "CANDY.SOFT"),
    ("sweet-snack",            "CANDY.SOFT"),
    # BISCUIT
    ("wafer",                  "BISCUIT.WAFER"),
    ("cracker",                "BISCUIT.CRACKER"),
    ("biscuit",                "BISCUIT.COOKIE"),
    ("cookie",                 "BISCUIT.COOKIE"),
    ("shortbread",             "BISCUIT.COOKIE"),
    # SNACK
    ("potato-crisp",           "SNACK.CHIP"),
    ("crisps",                 "SNACK.CHIP"),
    ("chips-and-fries",        "SNACK.CHIP"),
    ("chips",                  "SNACK.CHIP"),
    ("puffed",                 "SNACK.PUFFED"),
    ("puffed-snack",           "SNACK.PUFFED"),
    ("corn-snack",             "SNACK.PUFFED"),
    ("extruded-snack",         "SNACK.PUFFED"),
    ("salty-snack",            "SNACK.CHIP"),
    # DAIRY
    ("condensed-milk",         "DAIRY.CONDENSED"),
    ("sweetened-condensed",    "DAIRY.CONDENSED"),
    ("cheese",                 "DAIRY.CHEESE"),
    ("yogurt",                 "DAIRY.YOGURT"),
    ("yoghurt",                "DAIRY.YOGURT"),
    ("fermented-milk",         "DAIRY.YOGURT"),
    ("milk-powder",            "DAIRY.POWDER_MILK"),
    ("powdered-milk",          "DAIRY.POWDER_MILK"),
    ("infant-formula",         "DAIRY.POWDER_MILK"),
    ("fresh-milk",             "DAIRY.FRESH_MILK"),
    ("pasteurised-milk",       "DAIRY.FRESH_MILK"),
    ("uht-milk",               "DAIRY.FRESH_MILK"),
    ("milk-drink",             "DAIRY.FRESH_MILK"),
    ("dairy",                  "DAIRY.FRESH_MILK"),       # broad fallback
    # INSTANT
    ("instant-noodle",         "INSTANT.NOODLE"),
    ("instant-noodles",        "INSTANT.NOODLE"),
    ("ramen",                  "INSTANT.NOODLE"),
    ("instant-porridge",       "INSTANT.PORRIDGE"),
    ("instant-rice",           "INSTANT.PORRIDGE"),
    ("sausage",                "INSTANT.PROCESSED"),
    ("pate",                   "INSTANT.PROCESSED"),
    ("canned-meat",            "INSTANT.PROCESSED"),
    ("processed-meat",         "INSTANT.PROCESSED"),
]

# Keywords that suggest a product contains added sugar → CONSTRAINT_2
SUGAR_KEYWORDS = re.compile(
    r'\b(sugar|sucrose|đường|glucose|dextrose|fructose|siro|syrup|'
    r'mật\s*ong|honey|maltose|lactose|malt|caramel|saccharose)\b',
    re.IGNORECASE
)

# Keywords that suggest fried product → CONSTRAINT_3
FRIED_KEYWORDS = re.compile(
    r'\b(chiên|rán|fried|chip|crisp|crisps|fritter|fry)\b',
    re.IGNORECASE
)

# Minimum commas to consider ingredients parseable as a list
MIN_COMMAS_FOR_LIST = 2


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _map_category(tags_str: str) -> str | None:
    """Return first matching ViFoodKG category ID, or None."""
    if not isinstance(tags_str, str):
        return None
    tags_lower = tags_str.lower()
    for tag_fragment, cat_id in CATEGORY_MAP:
        if tag_fragment in tags_lower:
            return cat_id
    return None


def _is_parseable(ing: str) -> bool:
    """Heuristic: ingredients text looks like a parseable list."""
    if not isinstance(ing, str) or len(ing) < 20:
        return False
    return ing.count(",") >= MIN_COMMAS_FOR_LIST


def _has_sugar_signal(row: pd.Series) -> bool:
    """Product likely contains added sugar (triggers CONSTRAINT_2)."""
    ing = str(row.get("ingredients_raw", ""))
    name = str(row.get("name_raw", ""))
    cat = str(row.get("category", ""))
    return bool(SUGAR_KEYWORDS.search(ing + " " + name))


def _is_fried(row: pd.Series) -> bool:
    """Product likely fried/chip (triggers CONSTRAINT_3)."""
    ing  = str(row.get("ingredients_raw", ""))
    name = str(row.get("name_raw", ""))
    cat  = str(row.get("category", ""))
    return bool(FRIED_KEYWORDS.search(ing + " " + name + " " + cat))


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame) -> dict:
    n = len(df)
    report: dict = {"total_products": n, "checks": {}}

    # Assign categories first (used by later checks)
    df = df.copy()
    df["category"] = df["categories_tags"].apply(_map_category)

    # ------------------------------------------------------------------ C1
    mandatory = ["energy_kcal", "protein_g", "fat_g", "carb_g", "sodium_mg"]
    df["c1_all5"] = df[mandatory].notna().all(axis=1)
    missing_any = df[~df["c1_all5"]]

    per_field = {col: int(df[col].notna().sum()) for col in mandatory}
    c1 = {
        "description":   "All 5 mandatory nutrients present (CONSTRAINT_1)",
        "pass":          int(df["c1_all5"].sum()),
        "fail":          int((~df["c1_all5"]).sum()),
        "pass_pct":      round(df["c1_all5"].mean() * 100, 1),
        "per_field":     per_field,
        "main_gap":      min(per_field, key=per_field.get),
    }
    report["checks"]["C1_nutrients"] = c1

    # ------------------------------------------------------------------ C2
    # Products with sugar signal but missing sugar nutrient
    # (OFF data doesn't have sugar_100g → flag as "not checkable" but
    #  count products that will need it)
    df["has_sugar_signal"] = df.apply(_has_sugar_signal, axis=1)
    c2_needed = df["has_sugar_signal"].sum()
    c2 = {
        "description":  "Products needing SUGAR nutrient (CONSTRAINT_2)",
        "products_needing_sugar": int(c2_needed),
        "pct_of_total":  round(c2_needed / n * 100, 1),
        "note":          "OFF fetch did not include sugar_100g — add in Bước 2 pipeline",
    }
    report["checks"]["C2_sugar"] = c2

    # ------------------------------------------------------------------ C3
    df["is_fried"] = df.apply(_is_fried, axis=1)
    c3_needed = df["is_fried"].sum()
    c3 = {
        "description":   "Products needing FAT_SATURATED (CONSTRAINT_3)",
        "products_needing_fat_saturated": int(c3_needed),
        "pct_of_total":  round(c3_needed / n * 100, 1),
        "note":          "OFF fetch did not include saturated-fat_100g — add in Bước 2 pipeline",
    }
    report["checks"]["C3_saturated_fat"] = c3

    # ------------------------------------------------------------------ CAT
    cat_mapped   = df["category"].notna().sum()
    cat_unmapped = df["category"].isna().sum()
    cat_dist     = df["category"].value_counts().to_dict()
    c_cat = {
        "description":   "Product category assignable from OFF tags",
        "mapped":        int(cat_mapped),
        "unmapped":      int(cat_unmapped),
        "mapped_pct":    round(cat_mapped / n * 100, 1),
        "distribution":  {str(k): int(v) for k, v in cat_dist.items()},
        "unmapped_sample": df[df["category"].isna()]["name_raw"].head(5).tolist(),
    }
    report["checks"]["CAT_category"] = c_cat

    # ------------------------------------------------------------------ ING
    df["ing_parseable"] = df["ingredients_raw"].apply(_is_parseable)
    ing_ok   = df["ing_parseable"].sum()
    ing_fail = (~df["ing_parseable"]).sum()

    # Language breakdown: Vietnamese vs English vs mixed
    vi_pattern = re.compile(r'[àáảãạăắặẳẵâấầẩẫậèéẻẽẹêếềệểễìíỉĩịòóỏõọôốồổỗộơớờợởỡùúủũụưứừựửữỳýỷỹỵđ]', re.I)
    df["has_vi"] = df["ingredients_raw"].apply(
        lambda x: bool(vi_pattern.search(str(x)))
    )
    c_ing = {
        "description":    "Ingredients text parseable (≥20 chars, ≥2 commas)",
        "parseable":      int(ing_ok),
        "not_parseable":  int(ing_fail),
        "parseable_pct":  round(ing_ok / n * 100, 1),
        "has_vietnamese": int(df["has_vi"].sum()),
        "english_only":   int((~df["has_vi"]).sum()),
    }
    report["checks"]["ING_parseable"] = c_ing

    # ------------------------------------------------------------------ BRD
    df["has_brand"] = df["brand"].notna() & (df["brand"].str.strip() != "")
    brd_ok = df["has_brand"].sum()
    c_brd = {
        "description": "Product.brand is present (required field)",
        "present":     int(brd_ok),
        "missing":     int(n - brd_ok),
        "present_pct": round(brd_ok / n * 100, 1),
    }
    report["checks"]["BRD_brand"] = c_brd

    # ------------------------------------------------------------------ Recommendations
    recs = []
    if c1["pass_pct"] < 60:
        recs.append("CRITICAL: Nutrient fill rate too low — loosen CONSTRAINT_1 to 3 mandatory")
    elif c1["pass_pct"] < 80:
        recs.append(f"INFO: Nutrient fill rate {c1['pass_pct']}% — acceptable; main gap: {c1['main_gap']}")

    if c_cat["mapped_pct"] < 50:
        recs.append("WARNING: <50% products mapped to category — expand CATEGORY_MAP rules")

    if not df["has_vi"].any():
        recs.append("WARNING: No Vietnamese ingredients detected — LLM will need EN→VI translation")
    elif df["has_vi"].mean() < 0.3:
        recs.append("INFO: Most ingredients are English-only — ensure LLM prompt handles both")

    if c2["products_needing_sugar"] > 0:
        recs.append(
            f"ACTION: Add sugar_100g to OFF fetch & Bước 2 pipeline "
            f"({c2['products_needing_sugar']} products trigger CONSTRAINT_2)"
        )
    if c3["products_needing_fat_saturated"] > 0:
        recs.append(
            f"ACTION: Add saturated_fat_100g to OFF fetch & Bước 2 pipeline "
            f"({c3['products_needing_fat_saturated']} products trigger CONSTRAINT_3)"
        )

    report["recommendations"] = recs
    return report, df


# ---------------------------------------------------------------------------
# Print report
# ---------------------------------------------------------------------------

def print_report(report: dict) -> None:
    sep = "─" * 50

    print(f"\n{'='*50}")
    print(f"  Schema Validation Report")
    print(f"  Total products: {report['total_products']}")
    print(f"{'='*50}\n")

    for key, check in report["checks"].items():
        print(f"[{key}] {check['description']}")

        if key == "C1_nutrients":
            print(f"  PASS (all 5)     : {check['pass']:>4} / {report['total_products']}  ({check['pass_pct']}%)")
            print(f"  FAIL (missing ≥1): {check['fail']:>4}")
            print(f"  Per-field coverage:")
            for field, count in check["per_field"].items():
                bar = "█" * int(count / report["total_products"] * 20)
                pct = count / report["total_products"] * 100
                print(f"    {field:<20} {count:>3}/{report['total_products']}  {pct:>5.1f}%  {bar}")
            print(f"  Main gap: {check['main_gap']}")

        elif key == "C2_sugar":
            print(f"  Need SUGAR       : {check['products_needing_sugar']:>4} / {report['total_products']}  ({check['pct_of_total']}%)")
            print(f"  Note: {check['note']}")

        elif key == "C3_saturated_fat":
            print(f"  Need FAT_SAT     : {check['products_needing_fat_saturated']:>4} / {report['total_products']}  ({check['pct_of_total']}%)")
            print(f"  Note: {check['note']}")

        elif key == "CAT_category":
            print(f"  Mapped           : {check['mapped']:>4} / {report['total_products']}  ({check['mapped_pct']}%)")
            print(f"  Unmapped         : {check['unmapped']:>4}")
            print(f"  Distribution:")
            for cat, cnt in sorted(check["distribution"].items(), key=lambda x: -x[1]):
                print(f"    {cat:<25} {cnt:>3}")
            if check["unmapped_sample"]:
                print(f"  Unmapped samples: {check['unmapped_sample'][:3]}")

        elif key == "ING_parseable":
            print(f"  Parseable        : {check['parseable']:>4} / {report['total_products']}  ({check['parseable_pct']}%)")
            print(f"  Not parseable    : {check['not_parseable']:>4}")
            print(f"  Has Vietnamese   : {check['has_vietnamese']:>4}")
            print(f"  English-only     : {check['english_only']:>4}")

        elif key == "BRD_brand":
            print(f"  Has brand        : {check['present']:>4} / {report['total_products']}  ({check['present_pct']}%)")
            print(f"  Missing brand    : {check['missing']:>4}")

        print()

    print(f"{'='*50}")
    print("  Recommendations")
    print(f"{'='*50}")
    for rec in report["recommendations"]:
        print(f"  → {rec}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root     = Path(__file__).resolve().parents[2]
    csv_path = root / "data/processed/off_vietnam.csv"
    out_path = root / "data/processed/schema_validation_report.json"

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} products from {csv_path.name}")

    report, df_annotated = validate(df)
    print_report(report)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[ok] Report saved → {out_path}")
