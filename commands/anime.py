import re
import urllib.parse
from pathlib import Path

import pandas as pd
from rapidfuzz import process, fuzz

# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "anime_details.csv"

# ============================================================
# Load Database
# ============================================================

df = pd.read_csv(CSV_FILE)

ANIME_NAMES = sorted(
    df["anime_name"].dropna().unique().tolist()
)

# ============================================================
# Detect Anime Request
# ============================================================

KEYWORDS = [
    "anime",
    "episode",
    "ep",
    "watch",
    "give me",
    "send",
    "download",
]


def is_anime_request(text: str) -> bool:

    text = text.lower()

    if any(word in text for word in KEYWORDS):
        return True

    for anime in ANIME_NAMES:
        if anime.lower() in text:
            return True

    return False


# ============================================================
# Generate Thumbnail
# ============================================================

def generate_thumbnail(anime, season, episode):

    prompt = (
        f"Epic anime promotional thumbnail, "
        f"{anime}, "
        f"Season {season}, "
        f"Episode {episode}, "
        f"cinematic anime artwork, "
        f"dynamic action pose, "
        f"beautiful lighting, "
        f"professional streaming thumbnail, "
        f"high quality, "
        f"16:9, "
        f"masterpiece"
    )

    encoded = urllib.parse.quote(prompt)

    return (
        "https://image.pollinations.ai/prompt/"
        f"{encoded}"
        "?width=512"
        "&height=512"
        "&model=flux"
        "&nologo=true"
    )


# ============================================================
# Anime Search
# ============================================================

def handle_anime_request(text: str):

    episode = 1

    match = re.search(
        r"(?:episode|ep)?\s*(\d+)",
        text,
        re.IGNORECASE,
    )

    if match:
        episode = int(match.group(1))

    cleaned = re.sub(
        r"(episode|ep|anime|watch|give me|send|download|\d+)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.strip()

    result = process.extractOne(
        cleaned,
        ANIME_NAMES,
        scorer=fuzz.WRatio,
    )

    if not result or result[1] < 70:

        return {
            "type": "text",
            "text": "❌ I couldn't find that anime."
        }

    anime_name = result[0]

    rows = df[
        (df["anime_name"] == anime_name)
        &
        (df["episode"] == episode)
    ]

    if rows.empty:

        return {
            "type": "text",
            "text": f"❌ {anime_name} Episode {episode} was not found."
        }

    row = rows.iloc[0]

    thumbnail = generate_thumbnail(
        anime_name,
        row["season"],
        row["episode"],
    )

    message = (
        f"📺 𝗔𝗡𝗜𝗠𝗘: {anime_name}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌀 Season : {row['season']}\n"
        f"🎬 Episode : {row['episode']}\n"
        f"📅 Release : {row['release_year']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"▶ Watch Now\n"
        f"{row['link']}"
    )

    return {
        "type": "anime",
        "text": message,
        "thumbnail": thumbnail,
        "anime": anime_name,
        "season": int(row["season"]),
        "episode": int(row["episode"]),
        "link": row["link"],
    }
