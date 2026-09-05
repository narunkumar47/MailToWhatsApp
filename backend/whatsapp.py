import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# LOAD .ENV FROM PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)


# ============================================================
# WHATSAPP CONFIGURATION
# ============================================================

WHATSAPP_ACCESS_TOKEN = os.getenv(
    "WHATSAPP_ACCESS_TOKEN"
)

WHATSAPP_PHONE_NUMBER_ID = os.getenv(
    "WHATSAPP_PHONE_NUMBER_ID"
)

GRAPH_API_VERSION = os.getenv(
    "GRAPH_API_VERSION",
    "v25.0"
)


# ============================================================
# SEND WHATSAPP MESSAGE
# ============================================================

def send_whatsapp_message(
    recipient_phone_number,
    message
):
    """
    Send a text message using the Meta WhatsApp Cloud API.
    """

    if not WHATSAPP_ACCESS_TOKEN:
        raise ValueError(
            "WHATSAPP_ACCESS_TOKEN is not configured. "
            f"Expected .env file at: {ENV_FILE}"
        )

    if not WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError(
            "WHATSAPP_PHONE_NUMBER_ID is not configured. "
            f"Expected .env file at: {ENV_FILE}"
        )

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": (
            f"Bearer {WHATSAPP_ACCESS_TOKEN}"
        ),
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=30
    )

    if not response.ok:
        raise Exception(
            "WhatsApp API error: "
            f"{response.status_code} - "
            f"{response.text}"
        )

    return response.json()


# ============================================================
# CONFIGURATION CHECK
# ============================================================

if __name__ == "__main__":

    print(
        "WhatsApp module loaded successfully! ✅"
    )

    print(
        "Environment file:",
        ENV_FILE
    )

    print(
        "Environment file exists:",
        ENV_FILE.exists()
    )

    print(
        "Phone ID configured:",
        bool(WHATSAPP_PHONE_NUMBER_ID)
    )

    print(
        "Access token configured:",
        bool(WHATSAPP_ACCESS_TOKEN)
    )

    print(
        "Graph API version:",
        GRAPH_API_VERSION
    )