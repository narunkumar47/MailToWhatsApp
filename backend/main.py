from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import threading
import os

from googleapiclient.discovery import build

from backend.gmail import (
    authenticate_user_gmail,
    get_useful_emails
)

from backend.database import (
    create_tables,
    create_user,
    get_user,
    get_user_by_id,
    save_gmail_token,
    save_whatsapp_number,
    is_email_processed,
    mark_email_processed,
    increment_sent_count,
    set_monitoring_enabled,
    get_dashboard_stats,
    update_last_checked
)

from backend.oauth import create_google_flow
from backend.whatsapp import send_whatsapp_message
from backend.email_formatter import format_email_for_whatsapp
from backend.email_checker import start_email_checker

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)


app = FastAPI(
    title="MailToWhatsApp"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://mailtowhatsapp-frontend.onrender.com"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


create_tables()

oauth_flows = {}
_checker_thread = None


def start_background_checker():
    """Start the automatic Gmail checker once per backend process."""
    global _checker_thread

    if (
        _checker_thread is not None
        and _checker_thread.is_alive()
    ):
        return

    _checker_thread = threading.Thread(
        target=start_email_checker,
        name="mailtowhatsapp-email-checker",
        daemon=True
    )

    _checker_thread.start()


@app.on_event("startup")
def on_startup():
    start_background_checker()


@app.get("/")
def home():
    return {
        "message": "MailToWhatsApp backend is running!"
    }


@app.get("/health")
def health_check():
    checker_running = bool(
        _checker_thread
        and _checker_thread.is_alive()
    )

    return {
        "status": "healthy",
        "automation_checker_running": checker_running
    }


@app.post("/users")
def add_user(email: str):
    user_id = create_user(email)

    return {
        "message": "User created successfully",
        "user_id": user_id,
        "email": email
    }


@app.get("/users")
def find_user(email: str):
    user = get_user(email)

    if user is None:
        return {
            "message": "User not found"
        }

    return {
        "id": user["id"],
        "email": user["email"],
        "whatsapp_number": user["whatsapp_number"],
        "monitoring_enabled": bool(
            user["monitoring_enabled"]
        ),
        "created_at": user["created_at"]
    }


@app.get("/users/{user_id}")
def get_user_details(user_id: int):
    user = get_user_by_id(user_id)

    if user is None:
        return {
            "error": "User not found"
        }

    return {
        "id": user["id"],
        "email": user["email"],
        "gmail_connected": bool(
            user["gmail_token"]
        ),
        "whatsapp_number": user["whatsapp_number"],
        "monitoring_enabled": bool(
            user["monitoring_enabled"]
        ),
        "last_checked_at":
            user["last_checked_at"],
        "emails_sent_count":
            user["emails_sent_count"] or 0,
        "created_at":
            user["created_at"]
    }


@app.get("/users/{user_id}/stats")
def dashboard_stats(user_id: int):
    stats = get_dashboard_stats(user_id)

    if stats is None:
        return {
            "error": "User not found"
        }

    return stats


@app.post("/users/whatsapp")
def connect_whatsapp(
    user_id: int,
    whatsapp_number: str
):
    user = get_user_by_id(user_id)

    if user is None:
        return {
            "error": "User not found"
        }

    cleaned_number = "".join(
        character
        for character in whatsapp_number
        if character.isdigit()
    )

    if len(cleaned_number) < 10:
        return {
            "error": "Please provide a valid WhatsApp number."
        }

    save_whatsapp_number(
        user["email"],
        cleaned_number
    )

    return {
        "message": "WhatsApp number saved successfully! ✅",
        "user_id": user_id,
        "whatsapp_number": cleaned_number
    }


@app.post("/users/{user_id}/monitoring")
def update_monitoring(
    user_id: int,
    enabled: bool
):
    user = get_user_by_id(user_id)

    if user is None:
        return {
            "error": "User not found"
        }

    if enabled:
        if not user["gmail_token"]:
            return {
                "error": "Please connect Gmail first."
            }

        if not user["whatsapp_number"]:
            return {
                "error": "Please save your WhatsApp number first."
            }

    set_monitoring_enabled(
        user_id,
        enabled
    )

    return {
        "message": (
            "Automatic monitoring enabled! 🚀"
            if enabled
            else "Automatic monitoring disabled."
        ),
        "user_id": user_id,
        "monitoring_enabled": enabled
    }


@app.get("/auth/login")
def google_login():
    flow = create_google_flow()

    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
    )

    oauth_flows[state] = flow

    return RedirectResponse(
        url=authorization_url
    )


@app.get("/auth/callback")
def google_callback(request: Request):
    state = request.query_params.get("state")

    if (
        not state
        or state not in oauth_flows
    ):
        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/"
                "?error=invalid_oauth_state"
            )
        )

    flow = oauth_flows.pop(state)

    try:
        flow.fetch_token(
            authorization_response=str(
                request.url
            )
        )

        credentials = flow.credentials

        gmail_service = build(
            "gmail",
            "v1",
            credentials=credentials
        )

        profile = (
            gmail_service
            .users()
            .getProfile(
                userId="me"
            )
            .execute()
        )

        email = profile[
            "emailAddress"
        ]

        user_id = create_user(
            email
        )

        save_gmail_token(
            email,
            credentials.to_json()
        )

        frontend_url = (
            f"{FRONTEND_URL}/"
            f"?gmail_connected=true"
            f"&email={email}"
            f"&user_id={user_id}"
        )

        return RedirectResponse(
            url=frontend_url
        )

    except Exception as error:
        print(
            "Google OAuth error:",
            error
        )

        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}/"
                "?error=gmail_connection_failed"
            )
        )


@app.get("/emails")
def get_emails(
    user_id: int
):
    user = get_user_by_id(
        user_id
    )

    if user is None:
        return {
            "error": "User not found"
        }

    if not user["gmail_token"]:
        return {
            "error": "Gmail is not connected for this user"
        }

    gmail_service = (
        authenticate_user_gmail(
            user["gmail_token"]
        )
    )

    emails = get_useful_emails(
        gmail_service
    )

    update_last_checked(
        user_id
    )

    return {
        "user_id": user_id,
        "count": len(emails),
        "emails": emails
    }


@app.post("/whatsapp/test")
def whatsapp_test(
    phone_number: str,
    message: str = "Hello from MailToWhatsApp! 🚀"
):
    try:
        result = send_whatsapp_message(
            phone_number,
            message
        )

        return {
            "message":
                "WhatsApp message sent successfully! ✅",
            "result": result
        }

    except Exception as error:
        return {
            "error": str(error)
        }


@app.get("/emails/whatsapp-preview")
def whatsapp_email_preview(
    user_id: int
):
    user = get_user_by_id(
        user_id
    )

    if user is None:
        return {
            "error": "User not found"
        }

    if not user["gmail_token"]:
        return {
            "error": "Gmail is not connected for this user"
        }

    gmail_service = (
        authenticate_user_gmail(
            user["gmail_token"]
        )
    )

    emails = get_useful_emails(
        gmail_service
    )

    update_last_checked(
        user_id
    )

    if not emails:
        return {
            "message":
                "No useful emails found."
        }

    formatted_message = (
        format_email_for_whatsapp(
            emails[0]
        )
    )

    return {
        "user_id": user_id,
        "email": emails[0],
        "whatsapp_message":
            formatted_message
    }


@app.post("/emails/send-to-whatsapp")
def send_email_to_whatsapp(
    user_id: int
):
    user = get_user_by_id(
        user_id
    )

    if user is None:
        return {
            "error": "User not found"
        }

    if not user["gmail_token"]:
        return {
            "error":
                "Gmail is not connected for this user"
        }

    if not user["whatsapp_number"]:
        return {
            "error":
                "WhatsApp number is not connected for this user"
        }

    gmail_service = (
        authenticate_user_gmail(
            user["gmail_token"]
        )
    )

    emails = get_useful_emails(
        gmail_service
    )

    update_last_checked(
        user_id
    )

    new_emails = []

    for email in emails:
        if not is_email_processed(
            user_id,
            email["id"]
        ):
            new_emails.append(
                email
            )

    if not new_emails:
        return {
            "message":
                "No new emails to send. ✅",
            "sent_count": 0
        }

    sent_emails = []
    failed_emails = []

    for email in new_emails:
        whatsapp_message = (
            format_email_for_whatsapp(
                email
            )
        )

        try:
            result = send_whatsapp_message(
                user["whatsapp_number"],
                whatsapp_message
            )

            mark_email_processed(
                user_id,
                email["id"]
            )

            increment_sent_count(
                user_id
            )

            sent_emails.append({
                "email_id":
                    email["id"],
                "subject":
                    email["subject"],
                "whatsapp_result":
                    result
            })

        except Exception as error:
            failed_emails.append({
                "email_id":
                    email["id"],
                "subject":
                    email["subject"],
                "error":
                    str(error)
            })

    return {
        "message":
            "Email processing completed.",
        "sent_count":
            len(sent_emails),
        "failed_count":
            len(failed_emails),
        "sent_emails":
            sent_emails,
        "failed_emails":
            failed_emails
    }
