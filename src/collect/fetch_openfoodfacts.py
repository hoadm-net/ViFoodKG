"""
Bước 1.1: Thu thập sản phẩm Việt Nam từ Open Food Facts

API filter: countries_tags = en:vietnam
Output:
    data/raw/openfoodfacts/vietnam_raw.json   — raw API response (full)
    data/processed/off_vietnam.csv            — cleaned & filtered

Run:
    python src/collect/fetch_openfoodfacts.py
"""

import json
import time
import unicodedata
import csv
from pathlib import Path

import httpx
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
PAGE_SIZE = 100        # OFF API caps at ~100 regardless of requested size
REQUEST_DELAY = 2.0    # seconds between pages (polite + avoids rate-limit)
MAX_RETRIES = 4
USER_AGENT = "ViFoodKG-research/1.0 (hoadm.me@gmail.com)"

FIELDS = [
    "code",
    "product_name",
    "brands",
    "ingredients_text",
    "energy_100g",          # kJ — convert to kcal via ÷4.184
    "proteins_100g",
    "fat_100g",
    "carbohydrates_100g",
    "sodium_100g",          # grams (x1000 → mg)
    "categories_tags",
    "countries_tags",
]

# Columns that count towards "has nutrients"
NUTRIENT_FIELDS = [
    "energy_kcal",
    "protein_g",
    "fat_g",
    "carb_g",
    "sodium_mg",
]


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_page(page: int, client: httpx.Client) -> dict:
    params = {
        "action":        "process",
        "tagtype_0":     "countries",
        "tag_contains_0": "contains",
        "tag_0":         "vietnam",
        "json":          "1",
        "page":          page,
        "page_size":     PAGE_SIZE,
        "fields":        ",".join(FIELDS),
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = client.get(OFF_SEARCH_URL, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 5 * attempt
            print(f" [retry {attempt}/{MAX_RETRIES} in {wait}s]", end=" ", flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_all_raw(cache_path: Path) -> list[dict]:
    """
    Download all Vietnam products, with page-level checkpointing.

    - Final cache: cache_path (vietnam_raw.json)  — load on re-run, skips all fetching
    - Partial checkpoint: cache_path.with_suffix('.partial.json') — resume from last page
    """
    if cache_path.exists():
        print(f"[cache] Loading from {cache_path.name}")
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    partial_path = cache_path.with_suffix("").parent / (cache_path.stem + ".partial.json")
    all_products: list[dict] = []
    start_page = 1

    # Resume from partial checkpoint if it exists
    if partial_path.exists():
        with open(partial_path, encoding="utf-8") as f:
            checkpoint = json.load(f)
        all_products = checkpoint["products"]
        start_page  = checkpoint["next_page"]
        total_saved = checkpoint.get("total", "?")
        print(f"[resume] {len(all_products)} products, continuing from page {start_page} (total={total_saved})")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    total: int | None = None

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        page = start_page

        while True:
            print(f"  Fetching page {page}...", end=" ", flush=True)
            data = _fetch_page(page, client)

            products = data.get("products", [])
            if total is None:
                total = data.get("count", 0)
                page_count = -(-total // PAGE_SIZE)
                print(f"total={total}, pages={page_count}", end=" ")

            print(f"got {len(products)}")
            if not products:
                break

            all_products.extend(products)

            # Save checkpoint after every page
            with open(partial_path, "w", encoding="utf-8") as f:
                json.dump({"products": all_products, "next_page": page + 1, "total": total},
                          f, ensure_ascii=False)

            if len(all_products) >= (total or 0):
                break

            page += 1
            time.sleep(REQUEST_DELAY)

    # Save final cache and remove partial
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False)
    if partial_path.exists():
        partial_path.unlink()
    print(f"[ok] Raw cache → {cache_path}  ({len(all_products)} products)")

    return all_products


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

def _nfc(s) -> str:
    return unicodedata.normalize("NFC", s).strip() if isinstance(s, str) else ""


def _safe_float(val) -> float | None:
    try:
        f = float(val)
        return round(f, 3) if f >= 0 else None
    except (TypeError, ValueError):
        return None


def _energy_kcal(p: dict) -> float | None:
    """Convert energy_100g from kJ → kcal."""
    kj = _safe_float(p.get("energy_100g"))
    return round(kj / 4.184, 1) if kj is not None else None


def clean(raw: list[dict]) -> pd.DataFrame:
    rows = []
    for p in raw:
        barcode   = str(p.get("code", "")).strip()
        name_raw  = _nfc(p.get("product_name", ""))
        brand     = _nfc(p.get("brands", ""))
        ing_raw   = _nfc(p.get("ingredients_text", ""))
        cats      = "|".join(p.get("categories_tags") or [])
        countries = "|".join(p.get("countries_tags") or [])

        energy  = _energy_kcal(p)
        protein = _safe_float(p.get("proteins_100g"))
        fat     = _safe_float(p.get("fat_100g"))
        carb    = _safe_float(p.get("carbohydrates_100g"))

        sodium_g  = _safe_float(p.get("sodium_100g"))
        sodium_mg = round(sodium_g * 1000, 1) if sodium_g is not None else None

        nutrient_count = sum(
            x is not None
            for x in [energy, protein, fat, carb, sodium_mg]
        )

        rows.append({
            "barcode":       barcode,
            "name_raw":      name_raw,
            "brand":         brand,
            "ingredients_raw": ing_raw,
            "energy_kcal":   energy,
            "protein_g":     protein,
            "fat_g":         fat,
            "carb_g":        carb,
            "sodium_mg":     sodium_mg,
            "nutrient_count": nutrient_count,
            "categories_tags": cats,
            "countries_tags":  countries,
            "source":        "openfoodfacts",
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)

    # 1. Must have ingredients (at least 10 chars)
    has_ing = df["ingredients_raw"].str.len() >= 10
    df = df[has_ing]
    n1 = len(df)

    # 2. Must have >= 3 of the 5 mandatory nutrients
    df = df[df["nutrient_count"] >= 3]
    n2 = len(df)

    # 3. Dedup by barcode — keep entry with most nutrients, then longest ingredients
    df = df.sort_values(
        ["nutrient_count", "ingredients_raw"],
        ascending=[False, False],
        key=lambda col: col if col.name != "ingredients_raw" else col.str.len()
    )
    df = df.drop_duplicates(subset="barcode", keep="first")
    n3 = len(df)

    print(f"  Raw                  : {n0}")
    print(f"  Has ingredients      : {n1}  (-{n0-n1})")
    print(f"  ≥3 nutrients         : {n2}  (-{n1-n2})")
    print(f"  After dedup barcode  : {n3}  (-{n2-n3})")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(df: pd.DataFrame) -> None:
    total = len(df)
    print(f"\n{'─'*42}")
    print(f"  Products kept        : {total}")
    for col in NUTRIENT_FIELDS:
        filled = df[col].notna().sum()
        print(f"  {col:<20}: {filled:>4}  ({filled/total*100:.0f}%)")

    # Nutrient fill rate (5-nutrient complete)
    all5 = df[NUTRIENT_FIELDS].notna().all(axis=1).sum()
    print(f"  All 5 nutrients      : {all5:>4}  ({all5/total*100:.0f}%)")
    print(f"{'─'*42}\n")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[ok] CSV → {out_path}  ({len(df)} rows)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]

    cache_path = root / "data/raw/openfoodfacts/vietnam_raw.json"
    out_path   = root / "data/processed/off_vietnam.csv"

    print("=== Bước 1.1 — Open Food Facts VN ===\n")

    print("Fetching from OFF API ...")
    raw = fetch_all_raw(cache_path)
    print(f"  Total fetched        : {len(raw)}\n")

    print("Cleaning ...")
    df = clean(raw)

    print("\nFiltering ...")
    df = filter_df(df)

    print_stats(df)
    export(df, out_path)
