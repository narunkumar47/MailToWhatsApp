import re
from html import unescape


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_email_body(body):
    """
    Clean extracted Gmail content so it is suitable for WhatsApp.
    """

    if not body:
        return ""

    text = unescape(body)

    # --------------------------------------------------------
    # Remove URLs
    # --------------------------------------------------------

    text = re.sub(
        r"https?://\S+",
        " ",
        text
    )

    # Remove remaining www links
    text = re.sub(
        r"www\.\S+",
        " ",
        text
    )

    # --------------------------------------------------------
    # Remove common escaped URL fragments
    # --------------------------------------------------------

    text = re.sub(
        r"\\r\\n",
        "\n",
        text
    )

    text = re.sub(
        r"\\n",
        "\n",
        text
    )

    text = re.sub(
        r"\\t",
        " ",
        text
    )

    # --------------------------------------------------------
    # Remove HTML leftovers
    # --------------------------------------------------------

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # --------------------------------------------------------
    # Remove tracking / image filename leftovers
    # --------------------------------------------------------

    text = re.sub(
        r"\b[\w-]+\.(png|jpg|jpeg|gif|svg)\b",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Remove long tracking-token-looking strings
    # --------------------------------------------------------

    text = re.sub(
        r"\b[A-Za-z0-9_-]{60,}\b",
        " ",
        text
    )

    # --------------------------------------------------------
    # Remove excessive punctuation noise
    # --------------------------------------------------------

    text = re.sub(
        r"[|<>]{2,}",
        " ",
        text
    )

    # --------------------------------------------------------
    # Normalize whitespace
    # --------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    # Remove lines that are clearly just technical junk
    cleaned_lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Skip lines that are mostly technical URL characters
        if len(line) > 100 and sum(
            char in "/?=&_-"
            for char in line
        ) > 15:
            continue

        cleaned_lines.append(line)

    text = "\n".join(
        cleaned_lines
    ).strip()

    return text


# ============================================================
# REMOVE QUOTED REPLIES
# ============================================================

def remove_quoted_content(text):
    """
    Remove old quoted replies and common forwarded-message
    sections so WhatsApp only gets the current email.
    """

    if not text:
        return ""

    lines = text.splitlines()

    cleaned = []

    stop_patterns = [
        "-----original message-----",
        "----- forwarded message -----",
        "begin forwarded message",
        "original message",
        "wrote:",
    ]

    for line in lines:

        lower_line = line.lower().strip()

        if any(
            pattern in lower_line
            for pattern in stop_patterns
        ):
            break

        # Remove Gmail quoted reply lines
        if line.strip().startswith(">"):
            continue

        cleaned.append(
            line
        )

    return "\n".join(
        cleaned
    ).strip()


# ============================================================
# CREATE SUMMARY
# ============================================================

def create_email_summary(email):
    """
    Create a simple readable summary from the email body.

    This is intentionally rule-based for the MVP.
    AI summarization can be added later.
    """

    body = clean_email_body(
        email.get("body", "")
    )

    body = remove_quoted_content(
        body
    )

    if not body:
        return "No readable email content was available."

    # --------------------------------------------------------
    # Limit length
    # --------------------------------------------------------

    max_summary_length = 700

    if len(body) > max_summary_length:

        summary = (
            body[:max_summary_length]
            .rsplit(" ", 1)[0]
            .strip()
            + "..."
        )

    else:
        summary = body

    return summary


# ============================================================
# FORMAT EMAIL FOR WHATSAPP
# ============================================================

def format_email_for_whatsapp(email):
    """
    Format a useful Gmail email into a clean WhatsApp message.
    """

    sender = email.get(
        "sender",
        "Unknown sender"
    )

    subject = email.get(
        "subject",
        "No subject"
    )

    date = email.get(
        "date",
        ""
    )

    reason = email.get(
        "classification_reason",
        "Useful email"
    )

    score = email.get(
        "importance_score",
        0
    )

    summary = create_email_summary(
        email
    )

    message = (
        "📧 *Important Email*\n\n"
        f"👤 *From:* {sender}\n"
        f"📌 *Subject:* {subject}\n"
    )

    if date:
        message += (
            f"📅 *Date:* {date}\n"
        )

    message += (
        "\n"
        "📝 *Email Content:*\n"
        f"{summary}\n"
        "\n"
        f"🔎 *Why it matters:* {reason}\n"
        f"⭐ *Importance:* {score}\n"
        "\n"
        "━━━━━━━━━━━━━━\n"
        "MailToWhatsApp"
    )

    return message


# ============================================================
# SIMPLE TEST
# ============================================================

if __name__ == "__main__":

    test_email = {
        "sender": "John",
        "subject": "Are we meeting tomorrow?",
        "date": "Sat, 5 Sep 2026",
        "body": (
            "Hey Arun, just wanted to check if "
            "we are still meeting tomorrow at 10 AM."
        ),
        "classification_reason": "Likely personal email",
        "importance_score": 3
    }

    print(
        format_email_for_whatsapp(
            test_email
        )
    )