"""
ST-1.1: Parse openfoodfacts_additives_taxonomy.txt -> structured dict
ST-1.2: Map additives_classes -> AdditiveFunction vocabulary (ontology)

Run:
    python src/normalize/build_codex_lookup.py

Output:
    data/processed/codex_additives.json
    data/processed/codex_additives.csv
"""

import json
import re
import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# ST-1.2 — Mapping Codex function classes -> AdditiveFunction vocabulary
# ---------------------------------------------------------------------------
FUNCTION_MAP = {
    "en:colour":             "COLOR",
    "en:preservative":       "PRESERVATIVE",
    "en:antioxidant":        "ANTIOXIDANT",
    "en:emulsifier":         "EMULSIFIER",
    "en:stabiliser":         "STABILIZER",
    "en:thickener":          "THICKENER",
    "en:sweetener":          "SWEETENER",
    "en:flavour-enhancer":   "FLAVOR_ENHANCER",
    "en:acidity-regulator":  "ACIDITY_REGULATOR",
    "en:raising-agent":      "RAISING_AGENT",
    "en:sequestrant":        "SEQUESTRANT",
    "en:humectant":          "HUMECTANT",
    # mapped to OTHER
    "en:carrier":            "OTHER",
    "en:propellent-gas":     "OTHER",
    "en:coagulant":          "OTHER",
    "en:bulking-agent":      "OTHER",
    "en:foaming-agent":      "OTHER",
    "en:anti-caking-agent":  "OTHER",
    "en:flour-treatment-agent": "OTHER",
    "en:glazing-agent":      "OTHER",
}


def _map_functions(raw: str) -> list[str]:
    """'en:colour, en:stabiliser' -> ['COLOR', 'STABILIZER']"""
    result = []
    for part in raw.split(","):
        part = part.strip()
        mapped = FUNCTION_MAP.get(part, "OTHER")
        if mapped not in result:
            result.append(mapped)
    return result or ["OTHER"]


# ---------------------------------------------------------------------------
# ST-1.1 — Parser
# ---------------------------------------------------------------------------
E_NUMBER_PATTERN = re.compile(r"^E\d+", re.IGNORECASE)


def _is_e_number_entry(line: str) -> bool:
    """Check if 'en:' line is an E-number entry (not a synonym block)."""
    content = line[len("en:"):].strip()
    return bool(E_NUMBER_PATTERN.match(content))


def _extract_e_code(content: str) -> str:
    """'E100, Curcumin, ...' -> 'E100'"""
    return content.split(",")[0].strip().upper()


def _extract_names(content: str) -> tuple[str, list[str]]:
    """'E100, Curcumin, Turmeric extract, ...' -> ('Curcumin', ['Turmeric extract', ...])"""
    parts = [p.strip() for p in content.split(",")]
    names = [p for p in parts[1:] if p]  # skip E-number itself
    if not names:
        return "", []
    return names[0], names[1:]


def parse_taxonomy(filepath: Path) -> dict:
    """
    Parse the Open Food Facts additives taxonomy file.
    Returns dict keyed by E-number (e.g. 'E100').
    """
    records = {}
    current: dict | None = None

    with open(filepath, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            # Skip comments and stopwords/synonyms header blocks
            if line.startswith("#") or line.startswith("stopwords:") or line.startswith("synonyms:"):
                continue

            # Empty line → flush current record
            if line.strip() == "":
                if current:
                    records[current["e_number"]] = current
                    current = None
                continue

            # New E-number entry
            if line.startswith("en:") and _is_e_number_entry(line):
                # Flush previous if any
                if current:
                    records[current["e_number"]] = current

                content = line[len("en:"):].strip()
                e_code = _extract_e_code(content)
                name_en, aliases = _extract_names(content)

                current = {
                    "e_number":      e_code,
                    "ins_number":    None,
                    "name_en":       name_en,
                    "aliases_en":    aliases,
                    "name_vi":       None,
                    "function_types": [],
                    "wikidata_id":   None,
                    "permitted_in_vn": None,  # filled by ST-1.4
                }
                continue

            # Lines belonging to current record
            if current is None:
                continue

            if line.startswith("vi:"):
                content = line[len("vi:"):].strip()
                # 'E100, curcumin' -> take name after E-number
                parts = content.split(",", 1)
                if len(parts) == 2:
                    current["name_vi"] = parts[1].strip()

            elif line.startswith("additives_classes:en:"):
                raw = line[len("additives_classes:en:"):].strip()
                current["function_types"] = _map_functions(raw)

            elif line.startswith("wikidata:en:"):
                current["wikidata_id"] = line[len("wikidata:en:"):].strip()

            elif line.startswith("e_number:en:"):
                current["ins_number"] = line[len("e_number:en:"):].strip()

    # Flush last record
    if current:
        records[current["e_number"]] = current

    return records


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export(records: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "codex_additives.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[ok] JSON  → {json_path}  ({len(records)} entries)")

    csv_path = out_dir / "codex_additives.csv"
    fieldnames = ["e_number", "ins_number", "name_en", "name_vi",
                  "function_types", "wikidata_id", "permitted_in_vn", "aliases_en"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records.values():
            row = rec.copy()
            row["function_types"] = "|".join(rec["function_types"])
            row["aliases_en"]     = "|".join(rec["aliases_en"])
            writer.writerow(row)
    print(f"[ok] CSV   → {csv_path}")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def print_stats(records: dict) -> None:
    total       = len(records)
    has_vi      = sum(1 for r in records.values() if r["name_vi"])
    has_fn      = sum(1 for r in records.values() if r["function_types"] != ["OTHER"])
    has_wikidata = sum(1 for r in records.values() if r["wikidata_id"])

    print(f"\n{'─'*40}")
    print(f"  Total entries     : {total}")
    print(f"  Has name_vi       : {has_vi}  ({has_vi/total*100:.1f}%)")
    print(f"  Has function_type : {has_fn}  ({has_fn/total*100:.1f}%)")
    print(f"  Has wikidata_id   : {has_wikidata}  ({has_wikidata/total*100:.1f}%)")

    fn_counter: dict[str, int] = {}
    for r in records.values():
        for fn in r["function_types"]:
            fn_counter[fn] = fn_counter.get(fn, 0) + 1
    print(f"\n  Function type distribution:")
    for fn, count in sorted(fn_counter.items(), key=lambda x: -x[1]):
        print(f"    {fn:<22} {count}")
    print(f"{'─'*40}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    taxonomy_path = root / "data/raw/codex/openfoodfacts_additives_taxonomy.txt"
    out_dir       = root / "data/processed"

    print(f"Parsing {taxonomy_path.name} ...")
    records = parse_taxonomy(taxonomy_path)
    print_stats(records)
    export(records, out_dir)
