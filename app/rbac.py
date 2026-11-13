# Role-Based Access Control (RBAC)

def effective_roles(user):
    """Return the authenticated user's effective roles."""

    roles = set(user.get("roles", []))
    roles.add("Employee")

    department = user.get("department")

    if department:
        roles.add(department)

    return roles


def can_access(user, metadata):
    """
    Public website documents are accessible to every
    authenticated user.

    Private documents still require an allowed_roles match.
    """

    if not user or not user.get("username"):
        return False

    # Public website content: login is required,
    # but no particular department role is required.
    if metadata.get("access_scope") == "authenticated":
        return True

    # Existing department-level authorization.
    allowed_roles = set(metadata.get("allowed_roles", []))

    if not allowed_roles:
        return False

    user_roles = effective_roles(user)

    return bool(user_roles.intersection(allowed_roles))


