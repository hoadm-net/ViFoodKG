"""
ST-1.3 + ST-1.4: Enrich codex_additives.json with TT24/2019 data.

Source: data/raw/regulations/phu-luc-24-2019-TT-BYT.docx (Table 0)
- ST-1.3: name_vi from TT24 official Vietnamese names (fallback: name_en)
- ST-1.4: permitted_in_vn = True if INS found in TT24, else False

Run:
    python src/normalize/enrich_with_tt24.py

Output:
    data/processed/codex_additives.json  (updated in-place)
    data/processed/codex_additives.csv   (updated in-place)
"""

import json
import re
import csv
from pathlib import Path
from docx import Document


# ---------------------------------------------------------------------------
# Parse TT24 Phụ lục docx → lookup tables
# ---------------------------------------------------------------------------

def _normalize_ins(ins_raw: str) -> tuple[str, str]:
    """
    '100(i)'   -> base='100',  norm='100i'
    '160a(ii)' -> base='160a', norm='160aii'
    '102'      -> base='102',  norm='102'
    Returns (base, norm) both lowercase.
    """
    s = ins_raw.strip().lower()
    base = re.sub(r'\([^)]*\)', '', s).strip()
    norm = re.sub(r'[()]', '', s)
    return base, norm


def parse_tt24(docx_path: Path) -> tuple[dict, dict, set]:
    """
    Returns:
        tt24_by_norm  : {ins_norm: (name_vi, name_en)}
        tt24_by_base  : {ins_base: (name_vi, name_en)}  — first match wins
        permitted_bases: set of base INS strings
    """
    doc = Document(docx_path)
    tbl = doc.tables[0]  # Table 0 = full additive list

    tt24_by_norm: dict[str, tuple[str, str]] = {}
    tt24_by_base: dict[str, tuple[str, str]] = {}
    permitted_bases: set[str] = set()

    for row in tbl.rows[2:]:  # skip 2 header rows
        cells = [c.text.strip() for c in row.cells]
        if len(cells) < 3:
            continue

        ins_raw = cells[1]
        name_vi = cells[2]
        name_en = cells[3] if len(cells) > 3 else cells[2]

        if not ins_raw or not name_vi:
            continue

        base, norm = _normalize_ins(ins_raw)
        tt24_by_norm[norm] = (name_vi, name_en)
        permitted_bases.add(base)

        if base not in tt24_by_base:
            tt24_by_base[base] = (name_vi, name_en)

    return tt24_by_norm, tt24_by_base, permitted_bases


# ---------------------------------------------------------------------------
# Match Codex E-number to TT24 INS
# ---------------------------------------------------------------------------

def _e_number_suffix(e_num: str) -> str | None:
    """
    'E101(I)'  -> 'i'
    'E101(II)' -> 'ii'
    'E100'     -> None
    """
    m = re.search(r'\(([A-Z]+)\)$', e_num, re.I)
    return m.group(1).lower() if m else None


def enrich(records: dict, tt24_by_norm: dict, tt24_by_base: dict, permitted_bases: set) -> dict:
    matched_by_ins = 0
    matched_by_name = 0
    not_permitted = 0
    no_vi_name = 0

    # Build name_en → permitted set for fallback name matching
    # (lowercase stripped)
    tt24_name_en_map: dict[str, tuple[str, str]] = {
        v[1].lower().strip(): v
        for v in tt24_by_norm.values()
        if v[1]
    }

    for e_num, entry in records.items():
        ins_raw = (entry.get('ins_number') or '').strip().lower()
        name_en = (entry.get('name_en') or '').strip()

        # Try matching by INS number
        if ins_raw and ins_raw in permitted_bases:
            entry['permitted_in_vn'] = True

            # Try variant-specific match first (e.g. E101(I) → ins_norm='101i')
            suffix = _e_number_suffix(e_num)
            if suffix:
                norm_candidate = ins_raw + suffix
                if norm_candidate in tt24_by_norm:
                    entry['name_vi'] = tt24_by_norm[norm_candidate][0]
                    matched_by_ins += 1
                    continue

            # Fall back to base INS match
            if ins_raw in tt24_by_base:
                entry['name_vi'] = tt24_by_base[ins_raw][0]
                matched_by_ins += 1
                continue

        # Try matching by English name (for entries TT24 lists without INS variant)
        if not entry.get('permitted_in_vn'):
            name_key = name_en.lower()
            if name_key in tt24_name_en_map:
                entry['permitted_in_vn'] = True
                entry['name_vi'] = tt24_name_en_map[name_key][0]
                matched_by_name += 1
                continue

        # Not found in TT24 → not permitted
        entry['permitted_in_vn'] = False
        not_permitted += 1

        # name_vi fallback: use English name
        if not entry.get('name_vi'):
            entry['name_vi'] = name_en
            no_vi_name += 1

    print(f"  Matched by INS       : {matched_by_ins}")
    print(f"  Matched by EN name   : {matched_by_name}")
    print(f"  Not permitted in VN  : {not_permitted}")
    print(f"  name_vi fallback (EN): {no_vi_name}")

    return records


# ---------------------------------------------------------------------------
# Export (same format as build_codex_lookup.py)
# ---------------------------------------------------------------------------

def export(records: dict, out_dir: Path) -> None:
    json_path = out_dir / "codex_additives.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[ok] JSON  → {json_path}")

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
    total = len(records)
    permitted = sum(1 for r in records.values() if r.get('permitted_in_vn') is True)
    has_vi = sum(1 for r in records.values() if r.get('name_vi'))

    print(f"\n{'─'*40}")
    print(f"  Total entries       : {total}")
    print(f"  permitted_in_vn=True: {permitted}  ({permitted/total*100:.1f}%)")
    print(f"  Has name_vi         : {has_vi}  ({has_vi/total*100:.1f}%)")
    print(f"{'─'*40}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    docx_path = root / "data/raw/regulations/phu-luc-24-2019-TT-BYT.docx"
    json_path = root / "data/processed/codex_additives.json"
    out_dir   = root / "data/processed"

    print(f"Parsing TT24 docx: {docx_path.name} ...")
    tt24_by_norm, tt24_by_base, permitted_bases = parse_tt24(docx_path)
    print(f"  TT24 entries parsed : {len(tt24_by_norm)}")
    print(f"  Permitted INS bases : {len(permitted_bases)}")

    print(f"\nLoading {json_path.name} ...")
    with open(json_path, encoding="utf-8") as f:
        records = json.load(f)
    print(f"  Codex entries loaded: {len(records)}")

    print("\nEnriching ...")
    records = enrich(records, tt24_by_norm, tt24_by_base, permitted_bases)

    print_stats(records)
    export(records, out_dir)
