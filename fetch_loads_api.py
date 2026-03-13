import csv
import os
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_FILE = Path("daily_loads/load_export.csv")

API_SOURCE = os.getenv("API_SOURCE", "TRUCKSTOP")

# DAT
DAT_BASE_URL = os.getenv("DAT_BASE_URL", "")
DAT_API_KEY = os.getenv("DAT_API_KEY", "")

# Truckstop
TRUCKSTOP_TOKEN_URL = os.getenv("TRUCKSTOP_TOKEN_URL", "https://api-int.truckstop.com/auth/token")
TRUCKSTOP_SEARCH_URL = os.getenv("TRUCKSTOP_SEARCH_URL", "")
TRUCKSTOP_CLIENT_ID = os.getenv("TRUCKSTOP_CLIENT_ID", "")
TRUCKSTOP_CLIENT_SECRET = os.getenv("TRUCKSTOP_CLIENT_SECRET", "")

FIELDNAMES = [
    "pickup_city",
    "delivery_city",
    "trip_miles",
    "deadhead_miles",
    "weight_lbs",
    "rate",
    "broker",
    "stops",
]

SCAN_CITIES = {
    "Detroit MI", "Romulus MI", "Taylor MI", "Livonia MI",
    "Warren MI", "Flint MI", "Saginaw MI", "Toledo OH"
}
MAX_DEADHEAD = 150
MAX_TRIP = 500
MAX_WEIGHT = 9500


def fetch_truckstop_token():
    resp = requests.post(
        TRUCKSTOP_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": TRUCKSTOP_CLIENT_ID,
            "client_secret": TRUCKSTOP_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_truckstop_loads():
    token = fetch_truckstop_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Replace this payload with your real Truckstop search criteria
    payload = {
        "pageNumber": 1,
        "pageSize": 100
    }

    resp = requests.post(TRUCKSTOP_SEARCH_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_dat_loads():
    headers = {"Authorization": f"Bearer {DAT_API_KEY}"}
    resp = requests.get(DAT_BASE_URL, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def normalize_items(raw):
    items = raw.get("items", raw.get("loads", []))
    rows = []

    for item in items:
        pickup = item.get("pickup_city") or item.get("origin_city") or ""
        delivery = item.get("delivery_city") or item.get("destination_city") or ""
        trip_miles = float(item.get("trip_miles") or item.get("miles") or 0)
        deadhead_miles = float(item.get("deadhead_miles") or item.get("deadhead") or 0)
        weight_lbs = float(item.get("weight_lbs") or item.get("weight") or 0)
        rate = float(item.get("rate") or item.get("offer") or 0)
        broker = item.get("broker") or item.get("broker_name") or "Unknown"
        stops = int(float(item.get("stops") or item.get("stop_count") or 1))

        if pickup not in SCAN_CITIES:
            continue
        if deadhead_miles > MAX_DEADHEAD:
            continue
        if trip_miles > MAX_TRIP:
            continue
        if weight_lbs > MAX_WEIGHT:
            continue

        rows.append({
            "pickup_city": pickup,
            "delivery_city": delivery,
            "trip_miles": trip_miles,
            "deadhead_miles": deadhead_miles,
            "weight_lbs": weight_lbs,
            "rate": rate,
            "broker": broker,
            "stops": stops,
        })

    return rows


def save_csv(rows):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if API_SOURCE.upper() == "DAT":
        raw = fetch_dat_loads()
    else:
        raw = fetch_truckstop_loads()

    rows = normalize_items(raw)
    save_csv(rows)

    print(f"Fetched {len(rows)} loads")
    print(f"Saved: {OUTPUT_FILE}")
    print("Time:", datetime.now())


if __name__ == "__main__":
    main()
