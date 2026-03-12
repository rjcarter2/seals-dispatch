from twilio.rest import Client

TWILIO_ACCOUNT_SID = "PASTE_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "PASTE_TWILIO_AUTH_TOKEN"
TWILIO_FROM = "+18445267057"
TWILIO_TO = "+19892944631"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

message = client.messages.create(
    body="Test message from Seals Dispatch",
    from_=TWILIO_FROM,
    to=TWILIO_TO
)

print("Message SID:", message.sid)
print("Status:", message.status)