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

GRAPH_API_VERSION = "v23.0"
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


print("=" * 60)
print("Loaded .env:", ENV_FILE)
print("VERIFY_TOKEN:", VERIFY_TOKEN)
print("PAGE_ACCESS_TOKEN Loaded:", PAGE_ACCESS_TOKEN is not None)
print("=" * 60)


app = FastAPI()


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home():

    return {
        "status": "Kosto Facebook Bot Running",
        "verify_token_loaded": VERIFY_TOKEN is not None,
        "page_access_token_loaded": PAGE_ACCESS_TOKEN is not None
    }


# ============================================================
# WEBHOOK VERIFICATION
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

        return PlainTextResponse(
            content=challenge
        )

    print("❌ Verification Failed")

    return PlainTextResponse(
        "Verification failed",
        status_code=403
    )


# ============================================================
# SEND MESSENGER MESSAGE
# ============================================================

def send_message(recipient_id: str, text: str):

    url = (
        f"{GRAPH_API_URL}/me/messages"
        f"?access_token={PAGE_ACCESS_TOKEN}"
    )

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        print("\n========== SEND MESSAGE ==========")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        print("==================================")

        return response

    except Exception as e:

        print("Send Message Error:", e)

        return None


# ============================================================
# SEND IMAGE TO MESSENGER
# ============================================================

def send_image(recipient_id: str, image_url: str):

    url = (
        f"{GRAPH_API_URL}/me/messages"
        f"?access_token={PAGE_ACCESS_TOKEN}"
    )

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

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        print("\n========== SEND IMAGE ==========")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        print("================================")

        return response

    except Exception as e:

        print("Send Image Error:", e)

        return None


# ============================================================
# REPLY TO FACEBOOK COMMENT
# ============================================================

def reply_to_comment(comment_id: str, text: str):

    url = (
        f"{GRAPH_API_URL}/{comment_id}/comments"
        f"?access_token={PAGE_ACCESS_TOKEN}"
    )

    payload = {
        "message": text
    }

    print("\n========== COMMENT REPLY ==========")
    print("Comment ID:", comment_id)
    print("Reply     :", text)

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=20
        )

        print("Status Code:", response.status_code)
        print("Response   :", response.text)
        print("===================================")

        if response.ok:
            print("✅ Comment reply sent successfully")

        else:
            print("❌ Comment reply failed")

        return response

    except Exception as e:

        print("Comment Reply Error:", e)

        return None


# ============================================================
# HANDLE FACEBOOK COMMENT
# ============================================================

async def handle_comment(value: dict):

    comment_id = value.get("comment_id")
    comment_text = value.get("message")

    if not comment_id:

        print("⚠️ Comment ID missing")

        return

    if not comment_text:

        print("⚠️ Comment text missing")

        return

    print("\n========== NEW COMMENT ==========")
    print("Comment ID :", comment_id)
    print("Comment    :", comment_text)
    print("=================================")

    # --------------------------------------------------------
    # Ignore comments generated by our own Page
    # --------------------------------------------------------

    sender = value.get("from", {})
    sender_id = sender.get("id")

    page_id = value.get("post_id", "").split("_")[0]

    if sender_id and sender_id == page_id:

        print("⏭️ Ignoring Page's own comment")

        return

    # --------------------------------------------------------
    # Generate AI reply
    # --------------------------------------------------------

    try:

        reply = await generate_reply(
            f"comment_{comment_id}",
            comment_text
        )

    except Exception as e:

        print("Groq Comment Error:", e)

        return

    # --------------------------------------------------------
    # Handle different AI response types
    # --------------------------------------------------------

    if isinstance(reply, dict):

        if reply.get("type") == "text":

            reply = reply.get("text")

        else:

            print("⚠️ Unsupported AI response for comment")

            return

    if not reply:

        print("⚠️ No AI reply generated")

        return

    reply = str(reply).strip()

    print("\n========== GROQ COMMENT REPLY ==========")
    print(reply)
    print("========================================")

    # --------------------------------------------------------
    # Send reply to Facebook
    # --------------------------------------------------------

    reply_to_comment(
        comment_id,
        reply
    )


# ============================================================
# RECEIVE WEBHOOK EVENTS
# ============================================================

@app.post("/webhook")
async def webhook(request: Request):

    try:

        body = await request.json()

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid JSON"
            }
        )

    print("\n========== INCOMING EVENT ==========")

    print(
        json.dumps(
            body,
            indent=4,
            ensure_ascii=False
        )
    )

    print("====================================")


    # ========================================================
    # FACEBOOK PAGE EVENTS
    # ========================================================

    if body.get("object") == "page":

        for entry in body.get("entry", []):

            # =================================================
            # CHANGE EVENTS
            # =================================================

            for change in entry.get("changes", []):

                field = change.get("field")
                value = change.get("value", {})

                print("\n========== PAGE CHANGE ==========")
                print(
                    json.dumps(
                        value,
                        indent=4,
                        ensure_ascii=False
                    )
                )
                print("=================================")

                print("Change field:", field)

                # ------------------------------------------------
                # FACEBOOK COMMENT
                # ------------------------------------------------

                if (
                    field == "feed"
                    and value.get("item") == "comment"
                    and value.get("verb") == "add"
                ):

                    print("\n========== NEW COMMENT ==========")

                    print(
                        "Comment ID :",
                        value.get("comment_id")
                    )

                    print(
                        "Sender ID  :",
                        value.get("from", {}).get("id")
                    )

                    print(
                        "Comment    :",
                        value.get("message")
                    )

                    print("=================================")

                    await handle_comment(value)

            # =================================================
            # MESSENGER EVENTS
            # =================================================

            for event in entry.get("messaging", []):

                # ------------------------------------------------
                # Ignore non-message events
                # ------------------------------------------------

                if "message" not in event:

                    continue

                message = event["message"]

                # ------------------------------------------------
                # Ignore messages sent by Page itself
                # ------------------------------------------------

                if message.get("is_echo"):

                    continue

                sender_id = event["sender"]["id"]

                # ------------------------------------------------
                # Attachments
                # ------------------------------------------------

                if "text" not in message:

                    send_message(
                        sender_id,
                        "😅 আমি এখন শুধু text message বুঝতে পারি।"
                    )

                    continue

                user_text = message["text"].strip()

                print("\n========== MESSENGER MESSAGE ==========")
                print("Sender ID :", sender_id)
                print("Message   :", user_text)
                print("=======================================")

                try:

                    reply = await generate_reply(
                        sender_id,
                        user_text
                    )

                    # ==========================================
                    # ANIME
                    # ==========================================

                    if isinstance(reply, dict):

                        reply_type = reply.get("type")

                        if reply_type == "anime":

                            send_image(
                                sender_id,
                                reply["thumbnail"]
                            )

                            send_message(
                                sender_id,
                                reply["text"]
                            )

                        elif reply_type == "text":

                            send_message(
                                sender_id,
                                reply["text"]
                            )

                    # ==========================================
                    # CHARACTER IMAGE
                    # ==========================================

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

                    # ==========================================
                    # NORMAL AI REPLY
                    # ==========================================

                    elif reply:

                        send_message(
                            sender_id,
                            reply
                        )

                except Exception as e:

                    print("AI Error:", e)

                    send_message(
                        sender_id,
                        "😅 একটু সমস্যা হচ্ছে... কিছুক্ষণ পর আবার বলো।"
                    )


    # ============================================================
    # ALWAYS RETURN 200 TO FACEBOOK
    # ============================================================

    return JSONResponse(
        status_code=200,
        content={
            "status": "EVENT_RECEIVED"
        }
    )