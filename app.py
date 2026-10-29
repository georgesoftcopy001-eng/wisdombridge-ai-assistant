from flask import Flask, request
import os
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


@app.route("/", methods=["GET"])
def home():
    return "Wisdombridge AI Assistant is running!", 200


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
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    if message.get("type") != "text":
                        continue

                    sender = message.get("from")
                    text = message.get("text", {}).get("body", "")

                    if not sender or not text:
                        continue

                    if not OPENAI_API_KEY:
                        logging.error("OPENAI_API_KEY haijawekwa")
                        continue

                    ai_response = requests.post(
                        "https://api.openai.com/v1/responses",
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "gpt-4.1-mini",
                            "input": (
                                "Wewe ni msaidizi wa wateja wa Wisdombridge. "
                                "Jibu kwa Kiswahili rahisi, kwa heshima na ufupi. "
                                "Mteja akiuliza kuhusu vitabu, mwambie aombe katalogi. "
                                "Usidai malipo yamethibitishwa bila ushahidi.\n\n"
                                + text
                            ),
                        },
                        timeout=30,
                    )

                    if not ai_response.ok:
                        logging.error(
                            "OpenAI error %s: %s",
                            ai_response.status_code,
                            ai_response.text[:1000],
                        )
                        continue

                    output = ai_response.json().get("output", [])
                    reply = ""

                    for item in output:
                        for part in item.get("content", []):
                            if part.get("type") == "output_text":
                                reply += part.get("text", "")

                    if not reply.strip():
                        logging.error("OpenAI haikurudisha jibu")
                        continue

                    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
                        logging.error("WhatsApp credentials hazijakamilika")
                        continue

                    wa_response = requests.post(
                        f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages",
                        headers={
                            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "messaging_product": "whatsapp",
                            "to": sender,
                            "type": "text",
                            "text": {"body": reply[:4000]},
                        },
                        timeout=30,
                    )

                    if not wa_response.ok:
                        logging.error(
                            "WhatsApp error %s: %s",
                            wa_response.status_code,
                            wa_response.text[:1000],
                        )
                    else:
                        logging.info("Jibu limetumwa kwa WhatsApp")

    except Exception:
        logging.exception("Hitilafu kwenye webhook")

    return "OK", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
