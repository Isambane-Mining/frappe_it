"""One-time cleanup before the IT roles' core-DocType permissions move from
the Custom DocPerm fixture to frappe_it.setup.permissions.

Deletes every IT Manager / IT User Custom DocPerm row on a DocType this app
doesn't own - the old fixture rows (Read on Employee, Branch, Location, About
Us Settings, Data Import for IT User, ...) and any hand-made ones. The
after_migrate hook ensure_it_permissions then re-creates exactly the agreed
rows in the same migrate run. Other roles' rows are never touched; a DocType
left with no Custom DocPerm at all simply falls back to its standard
permissions.
"""

import frappe

IT_ROLES = ("IT Manager", "IT User")


def execute():
	own_doctypes = frappe.get_all("DocType", filters={"module": "Frappe IT"}, pluck="name")

	filters = {"role": ["in", IT_ROLES]}
	if own_doctypes:
		filters["parent"] = ["not in", own_doctypes]

	parents = set(frappe.get_all("Custom DocPerm", filters=filters, pluck="parent"))
	frappe.db.delete("Custom DocPerm", filters)

	for doctype in parents:
		frappe.clear_cache(doctype=doctype)
