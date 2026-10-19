# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Reveal a camera / NVR password to the IT roles.

The passwords are Password fields - encrypted (reversibly) in Frappe's __Auth
store, never shown in lists, reports or exports. Frappe's own
frappe.client.get_password only serves System Managers, so this lets the IT
roles read one back, one record at a time, and leaves an Info comment on the
record each time so reveals are auditable.
"""

import frappe
from frappe import _

DEVICE_DOCTYPES = ("IP Camera Details", "NVR Details")
REVEAL_ROLES = ("IT Manager", "IT User", "System Manager")


@frappe.whitelist(methods=["POST"])
def reveal_device_password(doctype, name):
	if doctype not in DEVICE_DOCTYPES:
		frappe.throw(_("Invalid Doctype: {0}").format(doctype))

	frappe.only_for(REVEAL_ROLES)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	password = doc.get_password("password", raise_exception=False)
	doc.add_comment("Info", _("Password revealed by {0}").format(frappe.session.user))
	return password
