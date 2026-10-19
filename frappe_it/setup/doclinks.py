# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Connections (DocType Link rows) this app adds to core DocTypes.

Rows are marked custom=1 - what Customize Form does - so syncing the core
DocType's JSON keeps them instead of replacing them; rows created before that
are upgraded in place. Duplicates from older runs are removed.
"""

import frappe

GROUP = "IT Resources"


def ensure_links(parent, required_links):
    existing = frappe.get_all(
        "DocType Link",
        filters={"parent": parent, "parenttype": "DocType"},
        fields=["name", "link_doctype", "link_fieldname", "custom"],
        order_by="creation asc",
    )

    ours = {(link["link_doctype"], link["link_fieldname"]) for link in required_links}
    by_key = {}
    for row in existing:
        key = (row.link_doctype, row.link_fieldname)
        if key not in ours:
            continue
        if key in by_key:
            frappe.db.delete("DocType Link", {"name": row.name})
        else:
            by_key[key] = row

    changed = False
    for link in required_links:
        row = by_key.get((link["link_doctype"], link["link_fieldname"]))
        if row:
            if not row.custom:
                frappe.db.set_value("DocType Link", row.name, "custom", 1, update_modified=False)
                changed = True
            continue

        frappe.get_doc(
            {
                "doctype": "DocType Link",
                "parent": parent,
                "parentfield": "links",
                "parenttype": "DocType",
                "group": GROUP,
                "custom": 1,
                **link,
            }
        ).insert(ignore_permissions=True)
        changed = True

    if changed:
        frappe.clear_cache(doctype=parent)
