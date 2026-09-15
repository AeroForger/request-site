"""Replace this module to use a different email provider."""

import json
import os
from urllib.request import Request, urlopen
from server.validation import TYPES


class MailUnavailable(Exception):
    pass


def send_request(data):
    key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("MAIL_FROM")
    recipient = os.environ.get("REQUEST_TO")
    if not all((key, sender, recipient)):
        raise MailUnavailable("Email service is not configured.")
    # Plain text avoids HTML injection. Recipient and sender are exclusively server configuration.
    message = {
        "from": sender,
        "to": [recipient],
        "reply_to": data["email"],
        "subject": "New Project Request",
        "text": f"New Project Request\n\nProject: {data['name']}\nType: {TYPES[data['type']]}\nBudget: {data['budget'] or 'Not specified'}\nContact: {data['email']}\n\nDescription:\n\n{data['description']}",
    }
    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(message).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "AeroForger-Portfolio/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            result = json.load(response)
            if not result.get("id"):
                raise MailUnavailable("Provider did not confirm acceptance.")
    except Exception as error:
        raise MailUnavailable("Email service unavailable.") from error
