from rbac import can_access


def test_public_website_available_to_all_authenticated_roles():

    website_document = {
        "access_scope": "authenticated",
        "allowed_roles": [],
        "domain": "madinps.edu.in",
    }

    users = [
        {
            "username": "finance.alice",
            "department": "Finance",
            "roles": ["Finance"],
        },
        {
            "username": "hr.bob",
            "department": "HR",
            "roles": ["HR"],
        },
        {
            "username": "marketing.user",
            "department": "Marketing",
            "roles": ["Marketing"],
        },
        {
            "username": "admin.user",
            "department": "Administration",
            "roles": ["C-Level"],
        },
    ]

    for user in users:
        assert can_access(user, website_document)


def test_private_finance_document_not_available_to_hr():

    private_document = {
        "department": "Finance",
        "allowed_roles": ["Finance", "C-Level"],
    }

    hr_user = {
        "username": "hr.bob",
        "department": "HR",
        "roles": ["HR"],
    }

    assert not can_access(hr_user, private_document)


def test_private_finance_document_available_to_finance():

    private_document = {
        "department": "Finance",
        "allowed_roles": ["Finance", "C-Level"],
    }

    finance_user = {
        "username": "finance.alice",
        "department": "Finance",
        "roles": ["Finance"],
    }

    assert can_access(finance_user, private_document)


def test_unauthenticated_user_cannot_access_website():

    website_document = {
        "access_scope": "authenticated",
        "allowed_roles": [],
    }

    assert not can_access(None, website_document)