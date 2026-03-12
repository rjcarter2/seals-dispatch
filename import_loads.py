import csv
from pathlib import Path
from datetime import datetime

IMPORTS_DIR = Path("imports")
OUTPUT_FILE = Path("daily_loads/load_export.csv")

# Change these mappings if your export uses different column names
COLUMN_MAP = {
    "pickup_city": ["pickup_city", "origin_city", "pickup", "origin"],
    "delivery_city": ["delivery_city", "destination_city", "delivery", "destination"],
    "trip_miles": ["trip_miles", "miles", "loaded_miles"],
    "deadhead_miles": ["deadhead_miles", "deadhead", "dh_miles"],
    "weight_lbs": ["weight_lbs", "weight", "weight_lb"],
    "rate": ["rate", "offer", "amount"],
    "broker": ["broker", "broker_name", "company"]
}

REQUIRED_COLUMNS = [
    "pickup_city",
    "delivery_city",
    "trip_miles",
    "deadhead_miles",
    "weight_lbs",
    "rate",
    "broker"
]

def find_latest_csv(folder: Path) -> Path | None:
    csv_files = list(folder.glob("*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=lambda f: f.stat().st_mtime)

def find_source_column(fieldnames, aliases):
    lowered = {name.lower().strip(): name for name in fieldnames}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    return None

def normalize_row(row, source_map):
    clean = {}
    for target, source_col in source_map.items():
        clean[target] = row.get(source_col, "").strip()
    return clean

def main():
    latest = find_latest_csv(IMPORTS_DIR)
    if latest is None:
        print("No CSV files found in imports folder.")
        return

    with open(latest, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        source_map = {}
        for target, aliases in COLUMN_MAP.items():
            source_col = find_source_column(fieldnames, aliases)
            if source_col is None:
                raise ValueError(f"Missing source column for '{target}'. Available columns: {fieldnames}")
            source_map[target] = source_col

        rows = [normalize_row(row, source_map) for row in reader]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Imported {len(rows)} loads from: {latest.name}")
    print(f"Saved normalized file to: {OUTPUT_FILE}")
    print("Import time:", datetime.now())

if __name__ == "__main__":
    main()