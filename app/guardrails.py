# Step 5: Implement guardrails
# This file will provide basic out-of-scope and PII(Personally Identifiable Information) protection.
import re

from rbac import effective_roles


SENSITIVE_PATTERNS = [
    # US Social Security Number
    re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),

    # Credit card-like number
    re.compile(
        r"\b(?:\d[ -]*?){13,19}\b"
    ),
]


def contains_sensitive_identifier(text):
    """
    Basic demo-level sensitive identifier detection.
    """

    for pattern in SENSITIVE_PATTERNS:

        if pattern.search(text):
            return True

    return False


def apply_output_guardrails(answer, user):
    """
    Apply a basic role-aware output guardrail.

    HR and C-Level are allowed to receive the
    protected identifiers covered by this demo policy.
    """

    if not contains_sensitive_identifier(answer):
        return answer

    roles = effective_roles(user)

    authorized_roles = {
        "HR",
        "C-Level",
    }

    if not roles.intersection(authorized_roles):

        return (
            "The response contains potentially "
            "sensitive personal information. "
            "Your role is not authorized to receive it."
        )

    return answer

