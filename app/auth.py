# Step 4: Implement authentication
# We will use bcrypt password hashes and store the user configuration in a Kubernetes Secret.

import os
import json
import bcrypt


def load_users():
    """
    Load the user directory from an environment variable.!
    """

    users_json = os.getenv(
        "CHATBOT_USERS_JSON",
        "{}",
    )

    return json.loads(users_json)


def authenticate(username, password):
    """
    Authenticate a user using bcrypt.

    Returns the authenticated user identity
    or None if authentication fails.
    """

    users = load_users()

    user_record = users.get(username)

    if not user_record:
        return None

    password_hash = user_record.get(
        "password_hash"
    )

    if not password_hash:
        return None

    try:
        valid_password = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    except ValueError:
        return None

    if not valid_password:
        return None

    return {
        "username": username,
        "department": user_record["department"],
        "roles": user_record["roles"],
    }