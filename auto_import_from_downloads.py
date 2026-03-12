from pathlib import Path
import shutil
from datetime import datetime

DOWNLOADS = Path(r"C:\Users\rjcar\Downloads")
IMPORTS = Path(r"C:\Users\rjcar\Downloads\Seals_Dispatch_Command_Center\imports")

KEYWORDS = ["dat", "truckstop", "load", "freight", "export"]

def latest_matching_csv(folder: Path):
    csvs = [f for f in folder.glob("*.csv") if any(k in f.name.lower() for k in KEYWORDS)]
    if not csvs:
        return None
    return max(csvs, key=lambda f: f.stat().st_mtime)

def main():
    IMPORTS.mkdir(parents=True, exist_ok=True)
    latest = latest_matching_csv(DOWNLOADS)

    if latest is None:
        print("No matching CSV export found in Downloads.")
        return

    target = IMPORTS / latest.name
    shutil.copy2(latest, target)

    print(f"Copied: {latest}")
    print(f"To: {target}")
    print("Time:", datetime.now())

if __name__ == "__main__":
    main()