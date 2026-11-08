import csv
import re
from collections import defaultdict
from pathlib import Path

# Common pharmaceutical salt & formulation suffixes to strip for clean root matching
SALT_SUFFIXES = re.compile(
    r"\b(HYDROCHLORIDE|HCL|SODIUM|POTASSIUM|SULFATE|MALEATE|BESYLATE|TARTRATE|"
    r"ACETATE|PHOSPHATE|CALCIUM|MESYLATE|CITRATE|SUCCINATE|FUMARATE|BROMIDE|"
    r"DISODIUM|DIHYDROCHLORIDE|MONOHYDRATE|HYDRATE|VALERATE|PROPIONATE)\b",
    re.IGNORECASE
)

def extract_orange_book_ingredients(orange_book_path: str) -> set[str]:
    """
    Parses FDA Orange Book products.txt (tilde '~' or tab delimited) 
    and returns a clean set of normalized active ingredient root names.
    """
    ob_path = Path(orange_book_path)
    if not ob_path.exists():
        raise FileNotFoundError(f"Orange Book file not found at: {orange_book_path}")

    print(f"Parsing Orange Book active ingredients from {orange_book_path}...")
    ingredients = set()

    with open(ob_path, mode="r", encoding="utf-8", errors="replace") as f:
        # Detect delimiter (FDA Orange Book typically uses tilde '~' or tab '\t')
        first_line = f.readline()
        delimiter = "~" if "~" in first_line else ("\t" if "\t" in first_line else ",")
        f.seek(0)

        reader = csv.DictReader(f, delimiter=delimiter)
        
        # Find column containing active ingredient names
        ingredient_col = None
        for col in reader.fieldnames or []:
            if col.strip().lower() in ["ingredient", "active_ingredient", "active ingredient"]:
                ingredient_col = col
                break

        if not ingredient_col:
            # Fallback to first column if header search fails
            ingredient_col = reader.fieldnames[0] if reader.fieldnames else None

        for row in reader:
            raw_ing = row.get(ingredient_col, "")
            if not raw_ing:
                continue

            # Ingredients with combinations are separated by ';'
            parts = raw_ing.split(";")
            for part in parts:
                cleaned = part.strip().upper()
                # Remove common salt/formulation terms (e.g., "ALBUTEROL SULFATE" -> "ALBUTEROL")
                root_name = SALT_SUFFIXES.sub("", cleaned).strip()
                # Clean up any leftover whitespace
                root_name = re.sub(r"\s+", " ", root_name)
                
                if len(root_name) >= 3:
                    ingredients.add(root_name.title())

    print(f"Found {len(ingredients)} unique active ingredient roots in Orange Book.")
    return ingredients


def filter_gsrs_with_orange_book(
    gsrs_path: str, 
    orange_book_path: str, 
    output_csv_path: str
):
    """
    Cross-references FDA GSRS UNII_Names.txt with active ingredients 
    from the FDA Orange Book to build a compact USAN <-> INN CSV.
    """
    # Step 1: Load active ingredients from Orange Book
    approved_ingredients = extract_orange_book_ingredients(orange_book_path)
    approved_lookup = {ing.lower(): ing for ing in approved_ingredients}

    gsrs_path_obj = Path(gsrs_path)
    if not gsrs_path_obj.exists():
        raise FileNotFoundError(f"GSRS file not found at: {gsrs_path}")

    print(f"Scanning GSRS dataset ({gsrs_path}) for approved ingredients...")

    # Group UNII records: unii -> set of distinct names
    unii_to_names = defaultdict(set)
    unii_to_preferred = {}

    with open(gsrs_path_obj, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        
        # Standardize header matching
        fieldmaps = {col.strip().upper(): col for col in reader.fieldnames or []}
        name_col = fieldmaps.get("NAME") or fieldmaps.get("NAME_TEXT") or fieldmaps.get("PT")
        unii_col = fieldmaps.get("UNII")
        type_col = fieldmaps.get("TYPE") or fieldmaps.get("NAME_TYPE")

        for row in reader:
            unii = row.get(unii_col, "").strip()
            name = row.get(name_col, "").strip().title()
            name_type = row.get(type_col, "").strip().upper() if type_col else ""

            if not unii or not name:
                continue

            # Skip chemical formulas, IUPAC notation, or long scientific names
            if any(char in name for char in ["-[", "]-", "(+", ")-", "Cyclo[", "Acid, "]) or len(name) > 60:
                continue

            unii_to_names[unii].add(name)
            
            if "PT" in name_type or "PREFERRED" in name_type or "PRIMARY" in name_type:
                unii_to_preferred[unii] = name

    # Step 2: Filter UNIIs that match an Orange Book active ingredient
    output_rows = []
    seen_pairs = set()

    for unii, names in unii_to_names.items():
        # Check if any name associated with this UNII matches an approved drug
        matched_approved_name = None
        for name in names:
            clean_name = SALT_SUFFIXES.sub("", name.upper()).strip()
            clean_name_title = re.sub(r"\s+", " ", clean_name).title()
            
            if clean_name_title.lower() in approved_lookup:
                matched_approved_name = approved_lookup[clean_name_title.lower()]
                break

        # If this UNII corresponds to an approved drug, pair its generic variants
        if matched_approved_name:
            name_list = sorted(list(names), key=len) # Prefer shorter generic terms
            
            # Pair distinct names for this approved drug UNII
            for i in range(len(name_list)):
                for j in range(i + 1, len(name_list)):
                    name_a, name_b = name_list[i], name_list[j]
                    
                    if name_a.lower() != name_b.lower():
                        # Avoid brand names or extreme length mismatches
                        pair_key = tuple(sorted([name_a, name_b])) + (unii,)
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            output_rows.append({
                                "usan_name": name_a,
                                "inn_name": name_b,
                                "unii_code": unii
                            })

    # Step 3: Write out to target CSV
    out_path = Path(output_csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, mode="w", encoding="utf-8", newline="") as out_file:
        fieldnames = ["usan_name", "inn_name", "unii_code"]
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nSuccess! Created {output_csv_path}")
    print(f"Total mapped generic rows: {len(output_rows)}")


if __name__ == "__main__":
    filter_gsrs_with_orange_book(
        gsrs_path="sources/UNII_Names_4Aug2026.txt",
        orange_book_path="sources/products.txt",
        output_csv_path="usan_inn_map.csv"
    )