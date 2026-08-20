import os
import re
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import AsyncGroq

from commands.anime import handle_anime_request, is_anime_request
from .role import SYSTEM_PROMPT


# ============================================================
# Load Environment
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)


# ============================================================
# Memory
# ============================================================

MEMORY_DIR = BASE_DIR / "runtime" / "roleplay_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Keywords
# ============================================================

IMAGE_KEYWORDS = [
    "photo",
    "picture",
    "image",
    "selfie",
    "pic",
    "show me",
    "send photo",
    "send image",
    "give me a photo",
    "ছবি",
    "ফটো",
    "একটা ছবি",
    "তোমার ছবি",
]

LOVE_KEYWORDS = [
    "love you",
    "i love you",
    "love u",
    "ভালোবাসি",
    "তোমাকে ভালোবাসি",
]


# ============================================================
# Memory Helpers
# ============================================================

def load_memory(uid: str):

    file = MEMORY_DIR / f"{uid}.json"

    if file.exists():

        try:
            return json.loads(
                file.read_text(encoding="utf-8")
            )

        except Exception:
            pass

    return {
        "uid": uid,
        "name": None,
        "likes_bot": False,
        "details": {},
        "history": [],
    }


def save_memory(uid: str, memory: dict):

    file = MEMORY_DIR / f"{uid}.json"

    file.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8",
    )


# ============================================================
# Helpers
# ============================================================

def detect_name(text: str):

    patterns = [
        r"(?:my name is|i am|i'm|i am called|আমার নাম|ami)\s+([A-Za-z\u0980-\u09FF]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

    return None


def is_image_request(text: str):

    text = text.lower()

    return any(
        word in text
        for word in IMAGE_KEYWORDS
    )


def is_love(text: str):

    text = text.lower()

    return any(
        word in text
        for word in LOVE_KEYWORDS
    )


def build_system_prompt(memory):

    prompt = SYSTEM_PROMPT

    if memory.get("name"):

        prompt += (
            f"\n\nব্যবহারকারীর নাম: {memory['name']}."
            "\nপ্রয়োজনে স্বাভাবিকভাবে নামটি ব্যবহার করতে পারো।"
        )

    if memory.get("likes_bot"):

        prompt += (
            "\nএই ব্যবহারকারী তোমার প্রতি পছন্দ প্রকাশ করেছে।"
            "\nস্বাভাবিক এবং উষ্ণভাবে কথা বলবে।"
        )

    return prompt


# ============================================================
# AI Chat
# ============================================================

async def generate_reply(
    sender_id: str,
    text: str
):

    if not GROQ_API_KEY:

        return "⚠️ GROQ_API_KEY সেট করা হয়নি।"

    memory = load_memory(sender_id)


    # --------------------------------------------------------
    # Remember Name
    # --------------------------------------------------------

    name = detect_name(text)

    if name and not memory.get("name"):

        memory["name"] = name


    # --------------------------------------------------------
    # Love Detection
    # --------------------------------------------------------

    if is_love(text):

        memory["likes_bot"] = True


    # --------------------------------------------------------
    # Image Request
    # --------------------------------------------------------

    if is_image_request(text):

        save_memory(
            sender_id,
            memory
        )

        return "__IMAGE__"


    # --------------------------------------------------------
    # Anime Request
    # --------------------------------------------------------

    if is_anime_request(text):

        return handle_anime_request(text)


    # --------------------------------------------------------
    # Build Conversation
    # --------------------------------------------------------

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(memory),
        }
    ]


    for item in memory["history"][-20:]:

        role = (
            "assistant"
            if item["role"] == "model"
            else item["role"]
        )

        messages.append(
            {
                "role": role,
                "content": item["text"],
            }
        )


    messages.append(
        {
            "role": "user",
            "content": text,
        }
    )


    # --------------------------------------------------------
    # Ask Groq
    # --------------------------------------------------------

    try:

        client = AsyncGroq(
            api_key=GROQ_API_KEY
        )

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=300,
        )

        reply = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as e:

        print("Groq Error:", e)

        reply = (
            "একটু সমস্যা হচ্ছে... "
            "কিছুক্ষণ পর আবার বলো।"
        )


    # --------------------------------------------------------
    # Save History
    # --------------------------------------------------------

    memory["history"].append(
        {
            "role": "user",
            "text": text,
        }
    )

    memory["history"].append(
        {
            "role": "model",
            "text": reply,
        }
    )


    memory["history"] = (
        memory["history"][-40:]
    )


    save_memory(
        sender_id,
        memory
    )


    return reply