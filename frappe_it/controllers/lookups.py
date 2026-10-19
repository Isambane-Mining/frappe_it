# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Whitelisted lookups for the IT forms.

The IT roles only hold Select (not Read) on Employee, Branch, Location and
Company, so the forms can't fetch those records with frappe.db.get_doc. These
return just the handful of fields the forms show, and only for a record the
caller is allowed to pick in a Link field (Select permission, which also
honours User Permissions on that record).
"""

import frappe
from frappe import _

HOLDER_DOCTYPES = ("Employee", "Asset", "Location")


@frappe.whitelist()
def get_holder_details(doctype, docname):
	"""Display name, site and designation of an Employee / Asset / Location."""
	if doctype not in HOLDER_DOCTYPES:
		frappe.throw(_("Invalid Doctype: {0}").format(doctype))

	if not docname or not frappe.db.exists(doctype, docname):
		return {}

	if not frappe.has_permission(doctype, "select", doc=docname):
		frappe.throw(_("Not permitted to select {0} {1}").format(_(doctype), docname), frappe.PermissionError)

	if doctype == "Employee":
		employee = frappe.db.get_value(
			"Employee", docname, ["employee_name", "branch", "designation"], as_dict=True
		)
		return {
			"name": employee.employee_name,
			"site": employee.branch,
			"designation": employee.designation,
		}

	if doctype == "Asset":
		asset = frappe.db.get_value("Asset", docname, ["item_name", "location"], as_dict=True)
		return {"name": asset.item_name, "site": asset.location, "designation": None}

	return {"name": docname, "site": docname, "designation": None}


@frappe.whitelist()
def get_current_employee():
	"""The session user's own Employee record, if any."""
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")


@frappe.whitelist()
def get_company_letter_head(company):
	if not company or not frappe.has_permission("Company", "select", doc=company):
		return None
	return frappe.db.get_value("Company", company, "default_letter_head")
