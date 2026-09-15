"""Validation shared by the API and its tests."""

import re

TYPES = {
    "cli": "CLI / Developer Tool",
    "desktop": "Desktop Application",
    "web": "Web Application",
    "embedded": "Embedded / Arduino",
    "library": "Library",
    "other": "Other",
}
LIMITS = {
    "type": (1, 20),
    "name": (2, 100),
    "description": (30, 5000),
    "budget": (0, 100),
    "email": (3, 254),
    "website": (0, 200),
}


def validate(payload):
    if not isinstance(payload, dict) or set(payload) - set(LIMITS):
        raise ValueError("Invalid request fields.")
    result = {}
    for key, (minimum, maximum) in LIMITS.items():
        value = payload.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"Invalid {key}.")
        value = value.strip()
        if not minimum <= len(value) <= maximum:
            raise ValueError(
                f"{key.capitalize()} must be between {minimum} and {maximum} characters."
            )
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
            raise ValueError(f"Invalid characters in {key}.")
        if key != "description" and ("\r" in value or "\n" in value):
            raise ValueError(f"Invalid characters in {key}.")
        result[key] = value
    if result["type"] not in TYPES:
        raise ValueError("Select a valid project type.")
    if not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+",
        result["email"],
    ):
        raise ValueError("Enter a valid contact email.")
    if result["website"]:
        raise ValueError("Unable to accept this request.")
    return result
