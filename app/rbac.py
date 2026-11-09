# Step 3: Implement role-based access control (RBAC)
# This file is the core authorisation logic.

def effective_roles(user):
    """
    Return the user's effective roles.

    Every authenticated user receives the Employee role
    and their assigned department role.
    """

    roles = set(user.get("roles", []))

    roles.add("Employee")

    department = user.get("department")

    if department:
        roles.add(department)

    return roles


def can_access(user, metadata):
    """
    Check whether a user can access a document.

    Default behavior: deny access if the document
    does not contain explicit allowed_roles metadata.
    """

    allowed_roles = set(
        metadata.get("allowed_roles", [])
    )

    if not allowed_roles:
        return False

    user_roles = effective_roles(user)

    return bool(
        user_roles.intersection(allowed_roles)
    )