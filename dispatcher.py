import csv
from datetime import datetime
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")


# -----------------------------
# TWILIO SETTINGS
# -----------------------------
TWILIO_ACCOUNT_SID = "PASTE_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "PASTE_TWILIO_AUTH_TOKEN"
TWILIO_FROM = "+19896258638"
TWILIO_TO = "+19892944631"
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_TO = os.getenv("TWILIO_TO")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

# -----------------------------
# SEALS DISPATCH SETTINGS
# -----------------------------
ORIGIN = "48601 Saginaw MI"
RADIUS = 500
DEADHEAD_LIMIT = 150

BASE_RATE_PER_MILE = 2.75
STOP_FEE = 50
MIN_RATE_PER_MILE = 2.25

# DETROIT FREIGHT SCANNER SETTINGS
SCAN_CITIES = [
    "Detroit MI",
    "Romulus MI",
    "Taylor MI",
    "Livonia MI",
    "Warren MI",
    "Flint MI",
    "Saginaw MI",
    "Toledo OH"
]

TARGET_TRUE_RPM = 3.50
HIGH_VALUE_TRUE_RPM = 4.00
MAX_WEIGHT_LBS = 9500
HISTORY_FILE = "load_history.csv"
PREFERRED_LANES = [
    "Detroit MI",
    "Flint MI",
    "Saginaw MI",
    "Toledo OH",
    "Grand Rapids MI",
    "Lansing MI",
    "Taylor MI",
    "Romulus MI",
    "Livonia MI",
    "Warren MI"
]

# -----------------------------
# LOAD BROKER SCORES
# -----------------------------
preferred_brokers = {}

with open("brokers.csv", "r", encoding="utf-8") as broker_file:
    broker_reader = csv.DictReader(broker_file)
    for broker_row in broker_reader:
        preferred_brokers[broker_row["broker"]] = int(broker_row["score"])

# -----------------------------
# LOAD INPUT
# -----------------------------
loads = []

with open("daily_loads/load_export.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for row in reader:
        pickup = row["pickup_city"]
        delivery = row["delivery_city"]

        trip_miles = float(row["trip_miles"])
        deadhead_miles = float(row["deadhead_miles"])
        weight_lbs = float(row["weight_lbs"])
        rate = float(row["rate"])
        broker = row["broker"]
        broker_score = preferred_brokers.get(broker, 0)
        stops = int(float(row.get("stops", 1) or 1))

        # Basic limits
        if deadhead_miles > DEADHEAD_LIMIT:
            continue

        if trip_miles > RADIUS:
            continue

        if weight_lbs > MAX_WEIGHT_LBS:
            continue    

        rpm = round(rate / trip_miles, 2)
        true_rpm = round(rate / (trip_miles + deadhead_miles), 2)

        # Filter weak loads
        if true_rpm < TARGET_TRUE_RPM:
            continue

        if pickup not in SCAN_CITIES:
            continue
        extra_stops = max(stops - 1, 0)

        fuel_cost = (trip_miles + deadhead_miles) * 0.80
        profit_score = round(rate - fuel_cost, 2)

        suggested_bid = round((trip_miles * BASE_RATE_PER_MILE) + (extra_stops * STOP_FEE))
        minimum_bid = round((trip_miles * MIN_RATE_PER_MILE) + (extra_stops * STOP_FEE))

        if rate < minimum_bid:
            bid_decision = "REJECT"
        elif rate < suggested_bid:
            bid_decision = "NEGOTIATE"
        else:
            bid_decision = "TAKE"

        if pickup in PREFERRED_LANES:
            lane_priority = 1
        else:
            lane_priority = 0

        loads.append({
            "pickup_city": pickup,
            "delivery_city": delivery,
            "trip_miles": trip_miles,
            "deadhead_miles": deadhead_miles,
            "weight_lbs": weight_lbs,
            "rate": rate,
            "broker": broker,
            "broker_score": broker_score,
            "stops": stops,
            "rpm": rpm,
            "true_rpm": true_rpm,
            "profit_score": profit_score,
            "suggested_bid": suggested_bid,
            "minimum_bid": minimum_bid,
            "bid_decision": bid_decision,
            "lane_priority": lane_priority,
            "scanner_match": "DETROIT FREIGHT SCANNER",
            "vehicle": "Box Truck"
        })

# -----------------------------
# SORT LOADS
# -----------------------------
loads = sorted(
    loads,
    key=lambda x: (x["true_rpm"], x["profit_score"], x["lane_priority"], x["broker_score"]),
    reverse=True
)

top_loads = loads[:10]
history_fields = [
    "scan_date",
    "pickup_city",
    "delivery_city",
    "trip_miles",
    "deadhead_miles",
    "weight_lbs",
    "rate",
    "broker",
    "broker_score",
    "stops",
    "rpm",
    "true_rpm",
    "profit_score",
    "suggested_bid",
    "minimum_bid",
    "bid_decision",
    "lane_priority"
]

try:
    with open(HISTORY_FILE, "x", newline="", encoding="utf-8") as history_file:
        writer = csv.DictWriter(history_file, fieldnames=history_fields)
        writer.writeheader()
except FileExistsError:
    pass

with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as history_file:
    writer = csv.DictWriter(history_file, fieldnames=history_fields)

    for load in loads:
        writer.writerow({
            "scan_date": datetime.now().strftime("%Y-%m-%d"),
            "pickup_city": load["pickup_city"],
            "delivery_city": load["delivery_city"],
            "trip_miles": int(load["trip_miles"]),
            "deadhead_miles": int(load["deadhead_miles"]),
            "weight_lbs": int(load["weight_lbs"]),
            "rate": int(load["rate"]),
            "broker": load["broker"],
            "broker_score": load["broker_score"],
            "stops": load["stops"],
            "rpm": load["rpm"],
            "true_rpm": load["true_rpm"],
            "profit_score": int(load["profit_score"]),
            "suggested_bid": int(load["suggested_bid"]),
            "minimum_bid": int(load["minimum_bid"]),
            "bid_decision": load["bid_decision"],
            "lane_priority": load["lane_priority"]
        })
lane_stats = {}

for load in loads:
    lane = f"{load['pickup_city']} -> {load['delivery_city']}"

    if lane not in lane_stats:
        lane_stats[lane] = {
            "count": 0,
            "total_true_rpm": 0,
            "total_profit": 0
        }

    lane_stats[lane]["count"] += 1
    lane_stats[lane]["total_true_rpm"] += load["true_rpm"]
    lane_stats[lane]["total_profit"] += load["profit_score"]

for lane, stats in lane_stats.items():
    stats["avg_true_rpm"] = round(stats["total_true_rpm"] / stats["count"], 2)
    stats["avg_profit"] = round(stats["total_profit"] / stats["count"], 2)
historical_lane_stats = {}

try:
    with open(HISTORY_FILE, "r", newline="", encoding="utf-8") as history_file:
        reader = csv.DictReader(history_file)

        for row in reader:
            lane = f"{row['pickup_city']} -> {row['delivery_city']}"
            true_rpm = float(row["true_rpm"])
            profit_score = float(row["profit_score"])

            if lane not in historical_lane_stats:
                historical_lane_stats[lane] = {
                    "count": 0,
                    "total_true_rpm": 0,
                    "total_profit": 0
                }

            historical_lane_stats[lane]["count"] += 1
            historical_lane_stats[lane]["total_true_rpm"] += true_rpm
            historical_lane_stats[lane]["total_profit"] += profit_score

except FileNotFoundError:
    pass

for lane, stats in historical_lane_stats.items():
    stats["avg_true_rpm"] = round(stats["total_true_rpm"] / stats["count"], 2)
    stats["avg_profit"] = round(stats["total_profit"] / stats["count"], 2)

historical_lane_stats = {}
# -----------------------------
# DISPLAY RESULTS
# -----------------------------
print("\nSEALS DISPATCH DETROIT FREIGHT SCANNER")
print(f"Origin: {ORIGIN}")
print(f"Radius: {RADIUS} miles")
print(f"Deadhead: {DEADHEAD_LIMIT} miles")
print(f"Target TRUE RPM: {TARGET_TRUE_RPM}\n")

for i, load in enumerate(top_loads, 1):
    print(f"{i}. {load['pickup_city']} -> {load['delivery_city']}")

    if load["true_rpm"] >= 5.00:
        print("   PREMIUM LOAD")

    if load["lane_priority"] == 1:
        print("   PREFERRED LANE")

    if load["true_rpm"] >= 4.00:
        strength = "HIGH VALUE LOAD"
    else:
        strength = "GOOD LOAD"

    print(f"   {strength}")
    print(f"   Vehicle: {load['vehicle']}")
    print(f"   Trip Miles: {int(load['trip_miles'])}  Deadhead: {int(load['deadhead_miles'])}")
    print(f"   Rate: ${int(load['rate'])}  RPM: ${load['rpm']}/mile  TRUE RPM: ${load['true_rpm']}/mile")
    print(f"   Profit Score: ${int(load['profit_score'])}")
    print(f"   Stops: {load['stops']}")
    print(f"   Suggested Bid: ${load['suggested_bid']} | Minimum Bid: ${load['minimum_bid']} | Decision: {load['bid_decision']}")
    print(f"   Broker: {load['broker']}  Broker Score: {load['broker_score']}\n")

# -----------------------------
# BEST LOAD
# -----------------------------
if not top_loads:
    print("No qualifying loads found.")
    print("Time:", datetime.now())
    raise SystemExit

best = top_loads[0]
print("TOP LANES")
print("BEST LOAD TODAY")
print(f"{best['pickup_city']} -> {best['delivery_city']}")
print(f"Vehicle: {best['vehicle']}")
print(f"Trip Miles: {int(best['trip_miles'])}  Deadhead: {int(best['deadhead_miles'])}")
print(f"Rate: ${int(best['rate'])}")
print(f"RPM: ${best['rpm']}/mile")
print(f"TRUE RPM: ${best['true_rpm']}/mile")
print(f"Profit Score: ${int(best['profit_score'])}")
print(f"Stops: {best['stops']}")
print(f"Suggested Bid: ${best['suggested_bid']}")
print(f"Minimum Bid: ${best['minimum_bid']}")
print(f"Decision: {best['bid_decision']}")
print(f"Broker: {best['broker']}\n")

# -----------------------------
# SAVE DAILY REPORT
# -----------------------------
today = datetime.now().strftime("%Y-%m-%d")
report_file = f"dispatch_report_{today}.txt"

with open(report_file, "w", encoding="utf-8") as report:
    report.write("SEALS DISPATCH DETROIT FREIGHT SCANNER\n")
    report.write(f"Date: {today}\n\n")
    report.write(f"Target TRUE RPM: {TARGET_TRUE_RPM}\n\n")

    for i, load in enumerate(top_loads, 1):
        report.write(f"{i}. {load['pickup_city']} -> {load['delivery_city']}\n")
        report.write(f"   Vehicle: {load['vehicle']}\n")
        report.write(f"   Trip Miles: {int(load['trip_miles'])}  Deadhead: {int(load['deadhead_miles'])}\n")
        report.write(f"   Rate: ${int(load['rate'])}\n")
        report.write(f"   TRUE RPM: ${load['true_rpm']}/mile\n")
        report.write(f"   Profit Score: ${int(load['profit_score'])}\n")
        report.write(f"   Stops: {load['stops']}\n")
        report.write(f"   Suggested Bid: ${load['suggested_bid']}\n")
        report.write(f"   Minimum Bid: ${load['minimum_bid']}\n")
        report.write(f"   Decision: {load['bid_decision']}\n")
        report.write(f"   Broker: {load['broker']}\n\n")
    report.write("TOP LANES\n")

    for lane, stats in sorted(lane_stats.items(), key=lambda x: x[1]["avg_true_rpm"], reverse=True)[:10]:
        report.write(
        f"{lane} | Loads: {stats['count']} | Avg TRUE RPM: ${stats['avg_true_rpm']}/mile | Avg Profit: ${int(stats['avg_profit'])}\n"
    )

    report.write("\n")
    report.write("\n")
    report.write("HISTORICAL TOP LANES\n")

for lane, stats in sorted(historical_lane_stats.items(), key=lambda x: x[1]["avg_true_rpm"], reverse=True)[:10]:
    report.write(
        f"{lane} | History Count: {stats['count']} | Avg TRUE RPM: ${stats['avg_true_rpm']}/mile | Avg Profit: ${int(stats['avg_profit'])}\n"
    )

    report.write("\n")
    report.write("BEST LOAD TODAY\n")
    report.write(f"{best['pickup_city']} -> {best['delivery_city']}\n")
    report.write(f"Rate: ${int(best['rate'])}\n")
    report.write(f"TRUE RPM: ${best['true_rpm']}/mile\n")
    report.write(f"Profit Score: ${int(best['profit_score'])}\n")
    report.write(f"Suggested Bid: ${best['suggested_bid']}\n")
    report.write(f"Minimum Bid: ${best['minimum_bid']}\n")
    report.write(f"Decision: {best['bid_decision']}\n")
    report.write(f"Broker: {best['broker']}\n")

# -----------------------------
# SMS ALERT
# ----------------------------- 
email_body = "SEALS DISPATCH DETROIT FREIGHT SCANNER\n\n"
email_body += f"Target TRUE RPM: {TARGET_TRUE_RPM}\n"
email_body += f"Total qualifying loads: {len(top_loads)}\n\n"
email_body += "TOP LANES\n"
for lane, stats in sorted(lane_stats.items(), key=lambda x: x[1]["avg_true_rpm"], reverse=True)[:5]:
    email_body += (
        f"{lane} | Loads: {stats['count']} | Avg TRUE RPM: ${stats['avg_true_rpm']}/mile | Avg Profit: ${int(stats['avg_profit'])}\n"
    )
email_body += "\n"
email_body += "HISTORICAL TOP LANES\n"
for lane, stats in sorted(historical_lane_stats.items(), key=lambda x: x[1]["avg_true_rpm"], reverse=True)[:5]:
    email_body += (
        f"{lane} | History: {stats['count']} | Avg TRUE RPM: ${stats['avg_true_rpm']}/mile | Avg Profit: ${int(stats['avg_profit'])}\n"
    )
email_body += "\n"

for i, load in enumerate(top_loads[:10], 1):
    email_body += (
        f"{i}. {load['pickup_city']} -> {load['delivery_city']}\n"
        f"Rate: ${int(load['rate'])} | TRUE RPM: ${load['true_rpm']}/mile | Profit: ${int(load['profit_score'])}\n"
        f"Bid: ${int(load['suggested_bid'])} | Min: ${int(load['minimum_bid'])} | {load['bid_decision']}\n"
        f"Broker: {load['broker']}\n\n"
    )

email_body += "BEST LOAD TODAY\n"
email_body += f"{best['pickup_city']} -> {best['delivery_city']}\n"
email_body += f"Rate: ${int(best['rate'])}\n"
email_body += f"TRUE RPM: ${best['true_rpm']}/mile\n"
email_body += f"Profit Score: ${int(best['profit_score'])}\n"
email_body += f"Suggested Bid: ${int(best['suggested_bid'])}\n"
email_body += f"Minimum Bid: ${int(best['minimum_bid'])}\n"
email_body += f"Decision: {best['bid_decision']}\n"
email_body += f"Broker: {best['broker']}\n"
try:
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_TO
    msg["Subject"] = "SEALS DISPATCH DETROIT FREIGHT SCANNER"

    msg.attach(MIMEText(email_body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

    print("Email alert sent successfully.")

except Exception as e:
    print("Email failed:")
    print(e)

print("Dispatch scan complete.")
print("Time:", datetime.now())
