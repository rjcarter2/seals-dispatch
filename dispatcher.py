import csv
from datetime import datetime
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_ADDRESS = "rjcarter2.rc@gmail.com"
EMAIL_PASSWORD = "PASTE_GMAIL_APP_PASSWORD""
EMAIL_TO = "rjcarter2.rc@gmail.com"
# -----------------------------
# TWILIO SETTINGS
# -----------------------------
TWILIO_ACCOUNT_SID = "PASTE_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "PASTE_TWILIO_AUTH_TOKEN"
TWILIO_FROM = "+19896258638"
TWILIO_TO = "+19892944631"

# -----------------------------
# SEALS DISPATCH SETTINGS
# -----------------------------
ORIGIN = "48601 Saginaw MI"
RADIUS = 500
DEADHEAD_LIMIT = 150

BASE_RATE_PER_MILE = 2.75
STOP_FEE = 50
MIN_RATE_PER_MILE = 2.25

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

        if weight_lbs > 9500:
            continue

        rpm = round(rate / trip_miles, 2)
        true_rpm = round(rate / (trip_miles + deadhead_miles), 2)

        # Filter weak loads
        if true_rpm < 3.50:
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

# -----------------------------
# DISPLAY RESULTS
# -----------------------------
print("\nSEALS DISPATCH SERVICES")
print(f"Origin: {ORIGIN}")
print(f"Radius: {RADIUS} miles")
print(f"Deadhead: {DEADHEAD_LIMIT} miles\n")

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
    print("Dispatch scan complete.")
    print("Time:", datetime.now())
    raise SystemExit

best = top_loads[0]

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
    report.write("SEALS DISPATCH SERVICES\n")
    report.write(f"Date: {today}\n\n")

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
email_body = f"""
SEALS DISPATCH BEST LOAD TODAY

{best['pickup_city']} -> {best['delivery_city']}

Vehicle: {best['vehicle']}
Trip Miles: {int(best['trip_miles'])}
Deadhead: {int(best['deadhead_miles'])}

Rate: ${int(best['rate'])}
RPM: ${best['rpm']}/mile
TRUE RPM: ${best['true_rpm']}/mile
Profit Score: ${int(best['profit_score'])}

Stops: {best['stops']}
Suggested Bid: ${best['suggested_bid']}
Minimum Bid: ${best['minimum_bid']}
Decision: {best['bid_decision']}

Broker: {best['broker']}
"""

try:
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_TO
    msg["Subject"] = "SEALS DISPATCH BEST LOAD TODAY"

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
print("Dispatch scan complete.")
print("Time:", datetime.now())