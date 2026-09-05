import base64
import json
import re
from email.utils import parseaddr
from html.parser import HTMLParser

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ============================================================
# CONFIGURATION
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]

MAX_BODY_LENGTH = 5000
MAX_EMAILS_TO_CHECK = 25


# ============================================================
# HTML -> CLEAN TEXT
# ============================================================

class EmailHTMLParser(HTMLParser):
    """
    Extract visible text from HTML emails.

    We deliberately ignore:
    - scripts
    - styles
    - head content
    - tracking elements
    - images
    """

    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "head",
            "noscript",
            "svg"
        }:
            self.skip_depth += 1
            return

        if self.skip_depth > 0:
            return

        if tag in {
            "br",
            "p",
            "div",
            "section",
            "article",
            "header",
            "footer",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag):

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "head",
            "noscript",
            "svg"
        }:
            if self.skip_depth > 0:
                self.skip_depth -= 1

            return

        if self.skip_depth > 0:
            return

        if tag in {
            "p",
            "div",
            "section",
            "article",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6"
        }:
            self.parts.append("\n")

    def handle_data(self, data):

        if self.skip_depth > 0:
            return

        text = data.strip()

        if text:
            self.parts.append(text)


def html_to_text(html):
    """
    Convert HTML email content into readable plain text.
    """

    if not html:
        return ""

    parser = EmailHTMLParser()

    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return ""

    text = " ".join(
        parser.parts
    )

    return clean_email_text(text)


# ============================================================
# CLEAN EMAIL TEXT
# ============================================================

def clean_email_text(text):
    """
    Clean Gmail email content.

    Handles:
    - HTML leftovers
    - URLs
    - tracking links
    - image links
    - markdown-style links
    - excessive whitespace
    - escaped characters
    """

    if not text:
        return ""

    # Decode common escaped newline/tab characters
    text = text.replace(
        "\\r\\n",
        "\n"
    )

    text = text.replace(
        "\\n",
        "\n"
    )

    text = text.replace(
        "\\t",
        " "
    )

    # Remove HTML comments
    text = re.sub(
        r"<!--.*?-->",
        " ",
        text,
        flags=re.DOTALL
    )

    # Remove remaining HTML tags
    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # --------------------------------------------------------
    # Convert markdown-like links
    #
    # [https://example.com]Some Text
    # [https://example.com]
    #
    # We want to keep "Some Text" and remove the URL.
    # --------------------------------------------------------

    text = re.sub(
        r"\[(?:https?://|www\.)[^\]]+\]",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # Remove angle-bracket URLs
    text = re.sub(
        r"<https?://[^>]+>",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # Remove ordinary URLs
    text = re.sub(
        r"https?://[^\s<>\]]+",
        " ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bwww\.[^\s<>\]]+",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Remove common image filenames
    # --------------------------------------------------------

    text = re.sub(
        r"\b[\w.-]+\.(?:png|jpg|jpeg|gif|svg|webp)\b",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Remove very long tracking tokens
    # --------------------------------------------------------

    text = re.sub(
        r"\b[A-Za-z0-9_-]{80,}\b",
        " ",
        text
    )

    # --------------------------------------------------------
    # Remove email HTML technical noise
    # --------------------------------------------------------

    technical_patterns = [
        r"\[if\s+[^\]]+\]",
        r"\[endif\]",
        r"\[endif\]--",
        r"\[if\s+false\]",
        r"\[if\s+mso\]",
    ]

    for pattern in technical_patterns:
        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE
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

    # Remove spaces around newlines
    text = re.sub(
        r" *\n *",
        "\n",
        text
    )

    text = text.strip()

    # --------------------------------------------------------
    # Remove obvious navigation-only lines
    # --------------------------------------------------------

    lines = []

    navigation_lines = {
        "download app",
        "download app now",
        "track order",
        "track your order",
        "unsubscribe",
        "view in browser",
        "view this email in browser",
        "manage preferences",
        "privacy policy",
        "terms of use",
    }

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.lower() in navigation_lines:
            continue

        # Skip lines that are almost entirely URL/tracking noise
        special_count = sum(
            char in "/?=&_|:-"
            for char in line
        )

        if (
            len(line) > 80
            and special_count > len(line) * 0.20
        ):
            continue

        lines.append(line)

    text = "\n".join(lines)

    # Final whitespace cleanup
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# DECODE GMAIL BODY
# ============================================================

def decode_gmail_body(data):
    """
    Decode Gmail's base64url encoded body.
    """

    if not data:
        return ""

    try:
        decoded = base64.urlsafe_b64decode(
            data + "=" * (-len(data) % 4)
        )

        return decoded.decode(
            "utf-8",
            errors="replace"
        )

    except Exception:
        return ""


# ============================================================
# EXTRACT BODY FROM MIME PARTS
# ============================================================

def extract_email_body(payload):
    """
    Extract the best readable body from a Gmail MIME payload.

    Preference:
        1. text/plain
        2. text/html converted to text
        3. nested multipart parts
    """

    if not payload:
        return ""

    mime_type = payload.get(
        "mimeType",
        ""
    )

    body_data = (
        payload
        .get("body", {})
        .get("data")
    )

    # --------------------------------------------------------
    # Plain text
    # --------------------------------------------------------

    if mime_type == "text/plain" and body_data:

        text = decode_gmail_body(
            body_data
        )

        return clean_email_text(
            text
        )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    if mime_type == "text/html" and body_data:

        html = decode_gmail_body(
            body_data
        )

        return html_to_text(
            html
        )

    # --------------------------------------------------------
    # Multipart
    # --------------------------------------------------------

    parts = payload.get(
        "parts",
        []
    )

    plain_text = ""
    html_text = ""

    for part in parts:

        part_mime = part.get(
            "mimeType",
            ""
        )

        extracted = extract_email_body(
            part
        )

        if not extracted:
            continue

        if part_mime == "text/plain":
            plain_text = extracted

        elif part_mime == "text/html":
            html_text = extracted

        # Nested multipart may itself return text.
        elif not plain_text:
            plain_text = extracted

    # Prefer real plain text
    if plain_text:
        return clean_email_text(
            plain_text
        )

    if html_text:
        return clean_email_text(
            html_text
        )

    return ""


# ============================================================
# HEADER HELPERS
# ============================================================

def get_header(headers, name):
    """
    Get a Gmail MIME header value.
    """

    name = name.lower()

    for header in headers or []:

        if header.get(
            "name",
            ""
        ).lower() == name:

            return header.get(
                "value",
                ""
            )

    return ""


def get_sender_name(sender_header):
    """
    Extract sender display name.
    """

    name, email_address = parseaddr(
        sender_header or ""
    )

    if name:
        return name

    if email_address:
        return email_address

    return "Unknown sender"


# ============================================================
# SENSITIVE EMAIL DETECTION
# ============================================================

def is_sensitive_email(subject, sender_email, body):
    """
    Detect OTP, verification and sensitive authentication
    emails that should NEVER be forwarded automatically.
    """

    subject = (subject or "").lower()
    sender_email = (sender_email or "").lower()
    body = (body or "").lower()

    text = " ".join([
        subject,
        sender_email,
        body
    ])

    sensitive_patterns = [

        # OTP / verification
        "one-time password",
        "one time password",
        "otp",
        "verification code",
        "verification code is",
        "security code",
        "security code is",
        "confirmation code",
        "confirmation code is",

        # Facebook / Meta
        "code to confirm this email address",
        "confirm this email address",
        "confirm your email address",
        "confirm your email",
        "verify your email address",

        # Account verification
        "verify your account",
        "verify this account",
        "verify your identity",
        "confirm your identity",

        # Password reset
        "password reset",
        "reset your password",
        "forgot your password",
        "change your password",

        # Login codes
        "login code",
        "log in code",
        "sign-in code",
        "sign in code",
        "authentication code",
        "authenticator code",

        # Magic links
        "magic link",
        "sign-in link",
        "sign in link",

    ]

    for pattern in sensitive_patterns:

        if pattern in text:
            return True

    # --------------------------------------------------------
    # Strong OTP structure
    # --------------------------------------------------------

    otp_patterns = [
        r"\b\d{4,8}\b.*\b(?:code|otp)\b",
        r"\b(?:code|otp)\b.*\b\d{4,8}\b",
    ]

    for pattern in otp_patterns:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            return True

    # --------------------------------------------------------
    # Known authentication senders
    # --------------------------------------------------------

    authentication_sender_patterns = [
        "security@facebookmail.com",
        "accounts.google.com",
        "account-security",
        "security-alert",
        "no-reply@accounts",
    ]

    for pattern in authentication_sender_patterns:

        if pattern in sender_email:

            auth_words = [
                "code",
                "verify",
                "confirm",
                "password",
                "login",
                "sign in",
                "security"
            ]

            if any(
                word in text
                for word in auth_words
            ):
                return True

    return False


# ============================================================
# PROMOTIONAL EMAIL DETECTION
# ============================================================

def is_promotional_email(
    subject,
    sender_email,
    body,
    list_unsubscribe="",
    precedence=""
):
    """
    Detect newsletters, advertisements and marketing emails.
    """

    subject = (subject or "").lower()
    sender_email = (sender_email or "").lower()
    body = (body or "").lower()
    list_unsubscribe = (
        list_unsubscribe or ""
    ).lower()
    precedence = (
        precedence or ""
    ).lower()

    text = " ".join([
        subject,
        sender_email,
        body
    ])

    # --------------------------------------------------------
    # Strong sender/domain signals
    # --------------------------------------------------------

    promotional_sender_patterns = [
        "newsletter",
        "marketing",
        "mailer",
        "mailing",
        "promotions",
        "promotion",
        "promo.",
        "offers.",
        "updates.",
        "deals.",
        "campaign",
        "notifications@",
    ]

    sender_signal = any(
        pattern in sender_email
        for pattern in promotional_sender_patterns
    )

    # --------------------------------------------------------
    # Strong subject signals
    # --------------------------------------------------------

    promotional_subject_patterns = [
        "sale",
        "flash sale",
        "limited time offer",
        "exclusive offer",
        "special offer",
        "discount",
        "off on",
        "% off",
        "coupon",
        "deal",
        "deals",
        "shop now",
        "buy now",
        "don't miss",
        "dont miss",
        "just for you",
        "new collection",
        "new arrivals",
        "summer collection",
        "winter collection",
        "beauty picks",
        "recommended for you",
        "trending now",
    ]

    subject_signal = any(
        pattern in subject
        for pattern in promotional_subject_patterns
    )

    # --------------------------------------------------------
    # Newsletter signals
    # --------------------------------------------------------

    newsletter_signal = (
        "list-unsubscribe" in text
        or bool(list_unsubscribe)
        or precedence in {
            "bulk",
            "list"
        }
    )

    # --------------------------------------------------------
    # Marketing body signals
    # --------------------------------------------------------

    marketing_body_patterns = [
        "unsubscribe",
        "manage your preferences",
        "view this email in browser",
        "shop now",
        "buy now",
        "use code",
        "promo code",
        "limited time",
        "offer ends",
    ]

    marketing_body_count = sum(
        1
        for pattern in marketing_body_patterns
        if pattern in body
    )

    # Strong newsletter
    if newsletter_signal:
        return True

    # Strong promotional sender + promotional subject
    if sender_signal and subject_signal:
        return True

    # Promotional subject + enough marketing content
    if subject_signal and marketing_body_count >= 1:
        return True

    # Strong marketing sender + enough marketing content
    if sender_signal and marketing_body_count >= 2:
        return True

    return False


# ============================================================
# IMPORTANCE SCORING
# ============================================================

def calculate_importance_score(
    subject,
    sender_email,
    body
):
    """
    Calculate a simple rule-based importance score.

    Higher score = more likely to be useful.
    """

    subject = (subject or "").lower()
    sender_email = (sender_email or "").lower()
    body = (body or "").lower()

    text = " ".join([
        subject,
        sender_email,
        body
    ])

    score = 0

    # --------------------------------------------------------
    # Account / security / access
    # --------------------------------------------------------

    account_patterns = [
        "account",
        "security alert",
        "account activity",
        "account update",
        "signed in",
        "new device",
        "new login",
        "permission",
        "access",
        "google account",
        "workspace",
    ]

    for pattern in account_patterns:

        if pattern in text:
            score += 3

    # --------------------------------------------------------
    # Transactions / orders / payments
    # --------------------------------------------------------

    transaction_patterns = [
        "order",
        "ordered",
        "delivery",
        "delivered",
        "shipment",
        "shipped",
        "refund",
        "payment",
        "invoice",
        "receipt",
        "transaction",
        "purchase",
        "booking",
        "reservation",
        "subscription",
        "renewal",
        "incident",
        "customer support",
        "support",
    ]

    for pattern in transaction_patterns:

        if pattern in text:
            score += 3

    # --------------------------------------------------------
    # Work / career
    # --------------------------------------------------------

    work_patterns = [
        "job",
        "career",
        "interview",
        "recruiter",
        "recruitment",
        "application",
        "hiring",
        "offer letter",
        "assessment",
        "internship",
        "internship opportunity",
        "placement",
        "employment",
        "meeting",
        "project",
        "deadline",
        "assignment",
    ]

    for pattern in work_patterns:

        if pattern in text:
            score += 3

    # --------------------------------------------------------
    # Personal communication
    # --------------------------------------------------------

    personal_patterns = [
        "please reply",
        "reply to this email",
        "can you",
        "could you",
        "let me know",
        "important",
        "urgent",
        "action required",
        "action needed",
        "reminder",
    ]

    for pattern in personal_patterns:

        if pattern in text:
            score += 2

    # --------------------------------------------------------
    # Sender signals
    # --------------------------------------------------------

    trusted_sender_patterns = [
        "google.com",
        "microsoft.com",
        "apple.com",
        "amazon.",
        "flipkart.com",
        "linkedin.com",
        "github.com",
        "deloitte.com",
        "college",
        "university",
    ]

    for pattern in trusted_sender_patterns:

        if pattern in sender_email:
            score += 2
            break

    return min(
        score,
        10
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_email(
    subject,
    sender_email,
    body,
    list_unsubscribe="",
    precedence=""
):
    """
    Decide whether an email should be forwarded.
    """

    subject = subject or ""
    sender_email = sender_email or ""
    body = body or ""

    # --------------------------------------------------------
    # 1. Sensitive emails ALWAYS rejected
    # --------------------------------------------------------

    if is_sensitive_email(
        subject,
        sender_email,
        body
    ):
        return {
            "useful": False,
            "score": 0,
            "reason": "Sensitive authentication or verification email"
        }

    # --------------------------------------------------------
    # 2. Promotional emails rejected
    # --------------------------------------------------------

    if is_promotional_email(
        subject,
        sender_email,
        body,
        list_unsubscribe,
        precedence
    ):
        return {
            "useful": False,
            "score": 0,
            "reason": "Promotional/newsletter email"
        }

    # --------------------------------------------------------
    # 3. Low-priority onboarding emails
    # --------------------------------------------------------

    text = " ".join([
        subject.lower(),
        sender_email.lower(),
        body.lower()
    ])

    onboarding_patterns = [
        "welcome to",
        "getting started",
        "thanks for signing up",
        "thanks for joining",
        "first step",
        "complete your profile",
        "activate your account",
        "introducing our community",
    ]

    if any(
        pattern in text
        for pattern in onboarding_patterns
    ):
        return {
            "useful": False,
            "score": 0,
            "reason": "Low-priority onboarding email"
        }

    # --------------------------------------------------------
    # 4. Calculate importance
    # --------------------------------------------------------

    score = calculate_importance_score(
        subject,
        sender_email,
        body
    )

    # --------------------------------------------------------
    # 5. Strongly useful emails
    # --------------------------------------------------------

    if score >= 5:
        return {
            "useful": True,
            "score": score,
            "reason": "Useful personal, work, account or transaction email"
        }

    # --------------------------------------------------------
    # 6. Moderate usefulness
    # --------------------------------------------------------

    if score >= 3:
        return {
            "useful": True,
            "score": score,
            "reason": "Likely useful email"
        }

    # --------------------------------------------------------
    # 7. Explicitly unimportant
    # --------------------------------------------------------

    return {
        "useful": False,
        "score": score,
        "reason": "Low-priority email"
    }


# ============================================================
# GET EMAIL DETAILS
# ============================================================

def get_email_details(
    service,
    message_id
):
    """
    Retrieve and parse one Gmail message.
    """

    message = (
        service
        .users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
        .execute()
    )

    payload = message.get(
        "payload",
        {}
    )

    headers = payload.get(
        "headers",
        []
    )

    sender_header = get_header(
        headers,
        "From"
    )

    sender_name = get_sender_name(
        sender_header
    )

    sender_email = parseaddr(
        sender_header
    )[1]

    subject = get_header(
        headers,
        "Subject"
    )

    date = get_header(
        headers,
        "Date"
    )

    list_unsubscribe = get_header(
        headers,
        "List-Unsubscribe"
    )

    precedence = get_header(
        headers,
        "Precedence"
    )

    # --------------------------------------------------------
    # Extract body
    # --------------------------------------------------------

    body = extract_email_body(
        payload
    )

    # --------------------------------------------------------
    # Gmail snippet fallback
    # --------------------------------------------------------

    if not body:

        body = clean_email_text(
            message.get(
                "snippet",
                ""
            )
        )

    # --------------------------------------------------------
    # Limit body size
    # --------------------------------------------------------

    if len(body) > MAX_BODY_LENGTH:

        body = (
            body[:MAX_BODY_LENGTH]
            .rsplit(" ", 1)[0]
            .strip()
            + "..."
        )

    classification = classify_email(
        subject,
        sender_email,
        body,
        list_unsubscribe,
        precedence
    )

    return {
        "id": message.get(
            "id"
        ),
        "thread_id": message.get(
            "threadId"
        ),
        "sender": sender_name,
        "sender_email": sender_email,
        "subject": subject or "No subject",
        "date": date,
        "body": body,
        "label_ids": message.get(
            "labelIds",
            []
        ),
        "list_unsubscribe": list_unsubscribe,
        "precedence": precedence,
        "importance_score": classification["score"],
        "classification_reason": classification["reason"],
        "_useful": classification["useful"],
    }


# ============================================================
# AUTHENTICATE USER GMAIL
# ============================================================

def authenticate_user_gmail(
    token_json
):
    """
    Rebuild Gmail credentials from the token saved in the DB.
    """

    if not token_json:
        raise ValueError(
            "Gmail token is missing."
        )

    try:
        token_data = json.loads(
            token_json
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Saved Gmail token is invalid."
        ) from error

    credentials = Credentials.from_authorized_user_info(
        token_data,
        SCOPES
    )

    # --------------------------------------------------------
    # Refresh expired token automatically
    # --------------------------------------------------------

    if credentials.expired and credentials.refresh_token:

        from google.auth.transport.requests import Request

        credentials.refresh(
            Request()
        )

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False
    )


# ============================================================
# GET USEFUL EMAILS
# ============================================================

def get_useful_emails(
    service,
    max_results=MAX_EMAILS_TO_CHECK
):
    """
    Fetch recent Gmail messages and return only useful ones.
    """

    response = (
        service
        .users()
        .messages()
        .list(
            userId="me",
            maxResults=max_results,
            q="newer_than:30d"
        )
        .execute()
    )

    messages = response.get(
        "messages",
        []
    )

    useful_emails = []

    print("\n========================================")
    print("        GMAIL EMAIL FILTER")
    print("========================================")

    print(
        f"Messages checked: {len(messages)}"
    )

    for message in messages:

        message_id = message.get(
            "id"
        )

        try:

            email = get_email_details(
                service,
                message_id
            )

            if email["_useful"]:

                useful_emails.append(
                    email
                )

                print(
                    f"\n✅ USEFUL | "
                    f"Score {email['importance_score']} | "
                    f"{email['subject']}"
                )

                print(
                    f"   From: {email['sender_email']}"
                )

                preview = email["body"][:250]

                if preview:
                    print(
                        f"   Body: {preview}"
                    )

            else:

                print(
                    f"\n❌ IGNORED | "
                    f"{email['classification_reason']} | "
                    f"{email['subject']}"
                )

        except Exception as error:

            print(
                f"\n⚠️ Could not process "
                f"email {message_id}: {error}"
            )

    print("\n========================================")
    print(
        f"Useful emails returned: {len(useful_emails)}"
    )
    print("========================================")

    return useful_emails


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Gmail module loaded successfully! ✅"
    )