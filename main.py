from pathlib import Path
import os
import json
import requests

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from dotenv import load_dotenv
from ai.ai import generate_reply
from ai.image_gen import generate_image

# ============================================================
# Load .env
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

print("=" * 60)
print("Loaded .env:", ENV_FILE)
print("VERIFY_TOKEN:", VERIFY_TOKEN)
print("PAGE_ACCESS_TOKEN Loaded:", PAGE_ACCESS_TOKEN is not None)
print("=" * 60)

app = FastAPI()
 

# ============================================================
# Home
# ============================================================

@app.get("/")
async def home():
    return {
        "status": "Messenger Bot Running",
        "verify_token_loaded": VERIFY_TOKEN is not None
    }


# ============================================================
# Webhook Verification
# ============================================================

@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print("\n========== WEBHOOK VERIFICATION ==========")
    print("Mode      :", mode)
    print("Token     :", token)
    print("Expected  :", VERIFY_TOKEN)
    print("Challenge :", challenge)
    print("==========================================")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Verification Successful")
        return PlainTextResponse(content=challenge)

    print("❌ Verification Failed")
    return PlainTextResponse("Verification failed", status_code=403)


# ============================================================
# Send Message
# ============================================================

def send_message(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v23.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }

    response = requests.post(url, json=payload)

    print("\n========== SEND MESSAGE ==========")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
    print("==================================")

def send_image(recipient_id: str, image_url: str):
    url = f"https://graph.facebook.com/v23.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True
                }
            }
        }
    }

    response = requests.post(url, json=payload)

    print(response.status_code)
    print(response.text)


# ============================================================
# Receive Webhook Events
# ============================================================

@app.post("/webhook")
async def webhook(request: Request):

    body = await request.json()

    print("\n========== INCOMING EVENT ==========")
    print(json.dumps(body, indent=4))
    print("====================================")

    if body.get("object") == "page":

        for entry in body.get("entry", []):

            for event in entry.get("messaging", []):

                # Ignore non-message events
                if "message" not in event:
                    continue

                message = event["message"]

                # Ignore messages sent by the page itself
                if message.get("is_echo"):
                    continue

                sender_id = event["sender"]["id"]

                # Ignore attachments for now
                if "text" not in message:
                    send_message(
                        sender_id,
                        "Sorry, I currently support text messages only."
                    )
                    continue

                user_text = message["text"].strip()

                print(f"Sender ID : {sender_id}")
                print(f"Message   : {user_text}")

                try:

                    reply = await generate_reply(
                        sender_id,
                        user_text
                    )

                    # ============================================================
                    # Anime
                    # ============================================================

                    if isinstance(reply, dict):

                        reply_type = reply.get("type")

                        if reply_type == "anime":

                            # Send thumbnail first
                            send_image(
                                sender_id,
                                reply["thumbnail"]
                            )

                            # Then send anime details
                            send_message(
                                sender_id,
                                reply["text"]
                            )

                        elif reply_type == "text":

                            send_message(
                                sender_id,
                                reply["text"]
                            )

                    # ============================================================
                    # Character Image
                    # ============================================================

                    elif reply == "__IMAGE__":

                        image = generate_image()

                        send_message(
                            sender_id,
                            image["text"]
                        )

                        send_image(
                            sender_id,
                            image["image_url"]
                        )

                    # ============================================================
                    # Normal AI Reply
                    # ============================================================

                    elif reply:

                        send_message(
                            sender_id,
                            reply
                        )

                except Exception as e:

                    print("AI Error:", e)

                    send_message(
                        sender_id,
                        "😅 Sorry, something went wrong."
                    )

    return JSONResponse(
        status_code=200,
        content={
            "status": "EVENT_RECEIVED"
        }
    )
