import urllib.parse
from datetime import datetime, timezone, timedelta

BANGLADESH_TZ = timezone(timedelta(hours=6))


def get_time_context():

    hour = datetime.now(BANGLADESH_TZ).hour

    if 5 <= hour < 12:
        return (
            "morning",
            "bright morning sunlight, college campus, fresh daylight",
        )

    elif 12 <= hour < 17:
        return (
            "afternoon",
            "afternoon sunlight, outdoors in Dhaka city, warm",
        )

    elif 17 <= hour < 20:
        return (
            "evening",
            "golden hour sunset, warm glowing light, beautiful sky",
        )

    else:
        return (
            "night",
            "cozy indoor room, soft warm lamp light, nighttime",
        )


def get_reply(time_of_day):

    replies = {
    "morning": "Starting your day with my photo? I approve. 😎📸",
    "afternoon": "I don't usually pose... but I'll make an exception. 😏",
    "evening": "Perfect lighting, perfect timing. Here's your photo. 🌅",
    "night": "The night gets a little brighter when I show up. 🌙📸",
}

    return replies.get(time_of_day, "এই নাও ছবি! 📸")


def generate_image():

    time_of_day, scene = get_time_context()

    prompt = (
    "high-quality anime illustration of Gojo Satoru, "
    "white spiky hair, piercing blue eyes, "
    "black modern outfit, confident expression, "
    f"{scene}, "
    "dynamic composition, cinematic lighting, "
    "8K, masterpiece, ultra detailed, "
    "professional anime artwork"
)

    encoded = urllib.parse.quote(prompt)

    seed = int(datetime.now(BANGLADESH_TZ).timestamp())

    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=512"
        f"&height=512"
        f"&seed={seed}"
        f"&nologo=true"
        f"&model=flux"
    )

    return {
        "text": get_reply(time_of_day),
        "image_url": image_url,
    }
