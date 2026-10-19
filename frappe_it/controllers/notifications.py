# Copyright (c) 2025, buff0k and contributors
# For license information, please see license.txt

"""Email the IT Managers when an Asset Request or Asset Return is first created.
Later edits and submission send nothing."""

import frappe

IT_ROLES = ("IT Manager",)

TEMPLATES = {
    "Asset Request": (
        "Asset Request for {employee_asset_name} ({allocate_to}) created",
        "An Asset Request for {employee_asset_name} ({allocate_to}) at {allocate_to_site} has been created by {actor}.",
    ),
    "Asset Return": (
        "Asset Return for {employee_name} ({employee}) created",
        "An Asset Return for {employee_name} ({employee}) at {branch} has been created by {actor}.",
    ),
}


def handle_doc_event_create(doc, method):
    templates = TEMPLATES.get(doc.doctype)
    if not templates:
        return

    recipients = _collect_recipients()
    if not recipients:
        return

    subject_template, body_template = templates
    values = doc.as_dict()
    actor = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    url = frappe.utils.get_url(doc.get_url())

    subject = subject_template.format(**values)
    body = body_template.format(**values, actor=actor)

    for email, full_name in recipients:
        message = "<br>".join(
            [
                f"Dear {full_name}",
                "",
                body,
                "",
                f'<a href="{url}">Click here to view</a>',
            ]
        )
        frappe.sendmail(recipients=[email], subject=subject, message=message)


def _collect_recipients():
    """(email, full name) for every enabled user holding an IT notification role."""
    users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", IT_ROLES], "parenttype": "User"},
        pluck="parent",
        distinct=True,
    )
    if not users:
        return []

    rows = frappe.get_all(
        "User",
        filters={"name": ["in", users], "enabled": 1, "email": ["is", "set"]},
        fields=["email", "full_name", "name"],
        order_by="email",
    )
    return [(row.email, row.full_name or row.name) for row in rows]
