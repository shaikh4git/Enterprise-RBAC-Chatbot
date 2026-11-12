
import os
import json
import bcrypt


def load_users():
    """Load users from the Kubernetes Secret environment variable."""

    users_json = os.getenv("CHATBOT_USERS_JSON", "{}")

    try:
        users = json.loads(users_json)

        if not isinstance(users, dict):
            raise ValueError("User configuration must be a JSON object")

        return users

    except (json.JSONDecodeError, ValueError) as exc:
        print(f"User configuration error: {exc}")
        return {}


def authenticate(username, password):
    """
    Authenticate a user using bcrypt.

    Returns authenticated user identity or None.
    """

    if not username or not password:
        return None

    users = load_users()

    username = username.strip().lower()

    user_record = users.get(username)

    if not user_record:
        return None

    password_hash = user_record.get("password_hash")

    if not password_hash:
        return None

    try:
        valid_password = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    except (ValueError, TypeError):
        return None

    if not valid_password:
        return None

    return {
        "username": username,
        "department": user_record.get("department", ""),
        "roles": user_record.get("roles", []),
    }
