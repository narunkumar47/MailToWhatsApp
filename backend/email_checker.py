import time

from backend.database import (
    get_connection,
    is_email_processed,
    mark_email_processed,
    update_last_checked,
    increment_sent_count
)

from backend.gmail import (
    authenticate_user_gmail,
    get_useful_emails
)

from backend.email_formatter import format_email_for_whatsapp
from backend.whatsapp import send_whatsapp_message


CHECK_INTERVAL = 60


def get_all_users():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE gmail_token IS NOT NULL
        AND whatsapp_number IS NOT NULL
        AND monitoring_enabled = 1
    """)

    users = cursor.fetchall()

    connection.close()

    return users


def has_processed_emails(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM processed_emails
        WHERE user_id = ?
        LIMIT 1
    """, (user_id,))

    result = cursor.fetchone()

    connection.close()

    return result is not None


def create_initial_baseline(user_id, emails):
    print(
        f"Creating initial email baseline for user {user_id}..."
    )

    baseline_count = 0

    for email in emails:
        try:
            mark_email_processed(
                user_id,
                email["id"]
            )

            baseline_count += 1

        except Exception as error:
            print(
                f"Could not baseline email {email['id']}:",
                error
            )

    print(
        f"Initial baseline created: "
        f"{baseline_count} email(s)."
    )

    return baseline_count


def process_user_emails(user):
    user_id = user["id"]

    print("\n================================")
    print(f"Checking user: {user_id}")
    print(f"Gmail: {user['email']}")
    print(f"WhatsApp: {user['whatsapp_number']}")
    print("================================")

    try:
        gmail_service = authenticate_user_gmail(
            user["gmail_token"]
        )

        emails = get_useful_emails(
            gmail_service
        )

        update_last_checked(user_id)

        print(
            f"Useful emails found: {len(emails)}"
        )

    except Exception as error:
        print(
            f"Could not check Gmail for user {user_id}:",
            error
        )

        update_last_checked(user_id)

        return 0

    if not has_processed_emails(user_id):

        print("No previous email history found.")

        create_initial_baseline(
            user_id,
            emails
        )

        print(
            "Existing emails will NOT be sent."
        )

        return 0

    new_emails = []

    for email in emails:

        if not is_email_processed(
            user_id,
            email["id"]
        ):
            new_emails.append(email)

    print(
        f"New useful emails: {len(new_emails)}"
    )

    if not new_emails:

        print("Nothing new. Waiting...")

        return 0

    sent_count = 0

    for email in new_emails:

        print("\n--------------------------------")
        print("NEW EMAIL DETECTED! 📧")
        print("From:", email["sender"])
        print("Subject:", email["subject"])
        print("Date:", email["date"])
        print("--------------------------------")

        whatsapp_message = format_email_for_whatsapp(
            email
        )

        print("\nWhatsApp message prepared:")
        print(whatsapp_message)

        try:

            send_whatsapp_message(
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

            sent_count += 1

            print(
                "WhatsApp message sent successfully! ✅"
            )

        except Exception as error:

            print(
                "WhatsApp delivery failed."
            )

            print(
                "Reason:",
                error
            )

            print(
                "Email was NOT marked as processed."
            )

    return sent_count


def check_all_users():

    users = get_all_users()

    print("\n")
    print("========================================")
    print("      MAILTOWHATSAPP AUTOMATION")
    print("========================================")
    print(
        f"Monitoring-enabled users: {len(users)}"
    )

    if not users:

        print(
            "No users currently have automatic monitoring enabled."
        )

        return

    total_sent = 0

    for user in users:

        try:

            total_sent += process_user_emails(
                user
            )

        except Exception as error:

            print(
                f"Error processing user {user['id']}:",
                error
            )

    print(
        f"\nTotal emails sent: {total_sent}"
    )


def start_email_checker():

    print("\n")
    print("========================================")
    print("   MailToWhatsApp Email Checker")
    print("========================================")
    print(
        "Automatic monitoring is running."
    )
    print(
        "Checking every 5 minutes."
    )
    print(
        "Press CTRL+C to stop."
    )

    while True:

        try:

            check_all_users()

        except Exception as error:

            print(
                "Email checker error:",
                error
            )

        print(
            f"\nNext check in "
            f"{CHECK_INTERVAL // 60} minutes..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


if __name__ == "__main__":
    start_email_checker()