from rbac import can_access


finance_user = {
    "username": "finance.alice",
    "department": "Finance",
    "roles": ["Finance"],
}


hr_user = {
    "username": "hr.bob",
    "department": "HR",
    "roles": ["HR"],
}


marketing_user = {
    "username": "marketing.carol",
    "department": "Marketing",
    "roles": ["Marketing"],
}


executive_user = {
    "username": "ceo",
    "department": "Executive",
    "roles": ["C-Level"],
}


finance_document = {
    "department": "Finance",
    "allowed_roles": [
        "Finance",
        "C-Level",
    ],
}


hr_document = {
    "department": "HR",
    "allowed_roles": [
        "HR",
        "C-Level",
    ],
}


general_document = {
    "department": "General",
    "allowed_roles": [
        "Employee",
        "C-Level",
    ],
}


def test_finance_can_access_finance():

    assert can_access(
        finance_user,
        finance_document,
    )


def test_marketing_cannot_access_finance():

    assert not can_access(
        marketing_user,
        finance_document,
    )


def test_hr_can_access_hr():

    assert can_access(
        hr_user,
        hr_document,
    )


def test_finance_cannot_access_hr():

    assert not can_access(
        finance_user,
        hr_document,
    )


def test_all_employees_can_access_general():

    assert can_access(
        marketing_user,
        general_document,
    )


def test_executive_can_access_finance():

    assert can_access(
        executive_user,
        finance_document,
    )


def test_executive_can_access_hr():

    assert can_access(
        executive_user,
        hr_document,
    )