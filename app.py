from flask import Flask, request
import os
import requests

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

@app.route("/", methods=["GET"])
def home():
    return "Wisdombridge AI Assistant is running!"

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True) or {}

    try:
        messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
        for message in messages:
            if message.get("type") != "text":
                continue

            sender = message["from"]
            text = message["text"]["body"]

            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4.1-mini",
                    "input": (
                        "Wewe ni msaidizi wa wateja wa Wisdombridge. "
                        "Jibu kwa Kiswahili rahisi, kwa heshima na ufupi. "
                        "Mteja akiuliza kuhusu vitabu, mwelekeze aombe katalogi. "
                        "Usidai malipo yamethibitishwa bila ushahidi.\n\n"
                        + text
                    )
                },
                timeout=30
            )

            if response.ok:
                answer = response.json().get("output", [])
                reply = ""
                for item in answer:
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            reply += part.get("text", "")

                if reply:
                    requests.post(
                        f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages",
                        headers={
                            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messaging_product": "whatsapp",
                            "to": sender,
                            "type": "text",
                            "text": {"body": reply[:4000]}
                        },
                        timeout=30
                    )

    except Exception as error:
        print("Webhook error:", error)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
