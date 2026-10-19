"""IP Camera Details / NVR Details passwords were plain Data fields; they are
now Password fields. Move each stored value into Frappe's encrypted __Auth
store and mask the column, as a normal save of a Password field would.

The orphaned Linked Cameras child table (replaced by the HTML panel on NVR
Details) still held plaintext copies of camera passwords; its password field
is gone, so the leftover column is blanked.
"""

import frappe
from frappe.utils.password import set_encrypted_password


def execute():
	for doctype in ("IP Camera Details", "NVR Details"):
		for row in frappe.get_all(doctype, fields=["name", "password"]):
			password = row.password or ""
			if not password or set(password) == {"*"}:
				continue
			set_encrypted_password(doctype, row.name, password, "password")
			frappe.db.set_value(doctype, row.name, "password", "*" * len(password), update_modified=False)

	if frappe.db.has_column("Linked Cameras", "password"):
		frappe.db.sql("update `tabLinked Cameras` set `password` = NULL")
