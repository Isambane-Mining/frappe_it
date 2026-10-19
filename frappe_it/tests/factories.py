# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Minimal records for frappe_it tests.

Employees and Assets are inserted with db_insert: the tests exercise this
app's custody sync, not HRMS / ERPNext validation (Asset needs a fixed-asset
Item, accounts, purchase details ...), and IntegrationTestCase rolls back.
"""

import frappe
from frappe.utils import nowdate


def test_company():
	return frappe.db.get_value("Company", {}, "name", order_by="creation asc")


def make_location(name):
	if not frappe.db.exists("Location", name):
		frappe.get_doc({"doctype": "Location", "location_name": name}).insert(ignore_permissions=True)
	return name


def make_employee(name, company=None):
	if not frappe.db.exists("Employee", name):
		doc = frappe.new_doc("Employee")
		doc.update(
			{
				"name": name,
				"first_name": name,
				"employee_name": name,
				"company": company or test_company(),
				"status": "Active",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
			}
		)
		doc.db_insert()
	return name


def make_item(item_code="_Test IT Item"):
	if not frappe.db.exists("Item", item_code):
		doc = frappe.new_doc("Item")
		doc.update({"name": item_code, "item_code": item_code, "item_name": item_code, "is_fixed_asset": 1})
		doc.db_insert()
	return item_code


def make_asset(name, location, submitted=False, custodian=None, company=None):
	make_item()
	if not frappe.db.exists("Asset", name):
		doc = frappe.new_doc("Asset")
		doc.update(
			{
				"name": name,
				"asset_name": name,
				"item_code": "_Test IT Item",
				"company": company or test_company(),
				"location": location,
				"custodian": custodian,
				"purchase_date": nowdate(),
				"docstatus": 1 if submitted else 0,
				"status": "Submitted" if submitted else "Draft",
			}
		)
		doc.db_insert()
	return name


def make_allocation(holder_type, holder, assets, site_type=None, site=None):
	doc = frappe.new_doc("Asset Allocation")
	doc.employee_or_asset = holder_type
	doc.allocated_to = holder
	doc.employee_asset_name = holder
	doc.branch_or_location = site_type or ("Branch" if holder_type == "Employee" else "Location")
	doc.site = site
	for asset in assets:
		doc.append("list_of_allocated_assets", {"asset": asset, "check_out_date": nowdate()})
	doc.insert(ignore_permissions=True)
	return doc
