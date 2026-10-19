# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""The IT roles' permissions on DocTypes this app doesn't own.

These used to ship as a Custom DocPerm fixture, but importing a Custom DocPerm
row onto a DocType that has none yet silently drops every standard DocPerm of
that DocType (Custom DocPerm replaces DocPerm wholesale once any exists). This
goes through frappe.permissions.setup_custom_perms instead, which copies the
DocType's standard permissions into Custom DocPerm first, so other roles keep
what they had.

Runs after every migrate and sets each listed row to exactly these rights -
hand edits to these particular rows are reverted; other rows are untouched.
The IT roles' rights on this app's own DocTypes live in their DocType JSON.
"""

import frappe
from frappe.permissions import setup_custom_perms

IT_ROLES = ("IT Manager", "IT User")

PTYPES = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)

# Pick a value in a Link field without being able to open or list records.
SELECT = ("select",)
# Create, view and edit - no delete, import or share.
MAINTAIN = ("select", "read", "write", "create", "report", "export", "print", "email")
# IT Manager also imports, so Data Import works for bulk asset registers.
MAINTAIN_AND_IMPORT = (*MAINTAIN, "import")
DATA_TOOL = ("select", "read", "write", "create", "report", "export", "import", "print", "email", "share")

IT_PERMISSIONS = {
	"Asset": {"IT Manager": MAINTAIN_AND_IMPORT, "IT User": MAINTAIN},
	"Item": {"IT Manager": MAINTAIN_AND_IMPORT, "IT User": MAINTAIN},
	"Item Group": {"IT Manager": MAINTAIN_AND_IMPORT, "IT User": MAINTAIN},
	"Asset Category": {"IT Manager": MAINTAIN_AND_IMPORT, "IT User": MAINTAIN},
	"Employee": {"IT Manager": SELECT, "IT User": SELECT},
	"Branch": {"IT Manager": SELECT, "IT User": SELECT},
	"Location": {"IT Manager": SELECT, "IT User": SELECT},
	"Company": {"IT Manager": SELECT, "IT User": SELECT},
	"Supplier": {"IT Manager": SELECT, "IT User": SELECT},
	"Brand": {"IT Manager": SELECT, "IT User": SELECT},
	"Data Import": {"IT Manager": DATA_TOOL},
	"Data Export": {"IT Manager": DATA_TOOL},
}


def ensure_it_permissions():
	for doctype, roles in IT_PERMISSIONS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		for role, rights in roles.items():
			if frappe.db.exists("Role", role):
				_set_rights(doctype, role, rights)

		frappe.clear_cache(doctype=doctype)


def _set_rights(doctype, role, rights):
	setup_custom_perms(doctype)

	values = {ptype: int(ptype in rights) for ptype in PTYPES}
	name = frappe.db.get_value(
		"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
	)

	if name:
		current = frappe.db.get_value("Custom DocPerm", name, list(PTYPES), as_dict=True)
		if any(int(current[ptype] or 0) != value for ptype, value in values.items()):
			frappe.db.set_value("Custom DocPerm", name, values)
		return

	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": doctype,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": role,
			"permlevel": 0,
			"if_owner": 0,
			**values,
		}
	).insert(ignore_permissions=True)
