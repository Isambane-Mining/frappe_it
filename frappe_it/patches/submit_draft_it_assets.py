"""Submit every Draft Asset in an IT Asset Category, so it can be allocated
(Asset Allocation only accepts submitted Assets) and moved with Asset
Movements.

On the IT register these are all "Existing Asset" entries with no purchase
document, no depreciation and no CWIP, so ERPNext posts no GL entries on
submit - it only records its own opening Receipt Asset Movement at the
Asset's location and custodian.

ERPNext refuses that Receipt when the custodian is an Employee of another
company, so such a custodian is cleared before submitting (custody can't be
recorded across companies in ERPNext anyway). Every cleared custodian and any
Asset ERPNext still refuses to submit is listed in one Error Log entry; the
Asset stays Draft and can be fixed and submitted by hand.

Runs before backfill_asset_custody, which then moves the newly submitted
Assets to their allocation's holder.
"""

import frappe

IT_ASSET_CATEGORIES = (
	"Cellular Telephone",
	"Laptop Computer",
	"IP Cameras",
	"Cellphone Simcards",
	"Wireless Mouse",
	"Computer Monitor",
	"Vehicle Mounted Radio",
	"Desktop Printer",
	"Wired USB Keyboard",
	"Handheld Radio",
	"Desktop Computer",
	"USB Storage Devices",
	"Cell Phone Charger",
	"Laptop Stand",
	"LTE Router",
	"Network Printer",
	"NVRs",
	"LTE Modem",
	"Laptop Bag",
	"Laptop Chargers",
	"Software Licence",
)


def execute():
	drafts = frappe.get_all(
		"Asset",
		filters={"docstatus": 0, "asset_category": ["in", IT_ASSET_CATEGORIES]},
		fields=["name", "company", "custodian"],
		order_by="name",
	)

	notes = []
	for row in drafts:
		frappe.db.savepoint("frappe_it_submit_asset")
		try:
			asset = frappe.get_doc("Asset", row.name)

			if asset.custodian:
				employee_company = frappe.db.get_value("Employee", asset.custodian, "company")
				if employee_company != asset.company:
					notes.append(
						f"{asset.name}: custodian {asset.custodian} ({employee_company}) cleared - "
						f"Asset belongs to {asset.company}"
					)
					asset.custodian = None

			asset.flags.ignore_permissions = True
			asset.submit()
		except Exception as e:
			frappe.db.rollback(save_point="frappe_it_submit_asset")
			frappe.clear_messages()
			notes.append(f"{row.name}: NOT submitted - {e}")

	if notes:
		frappe.log_error(
			title="frappe_it: Draft IT Asset submission notes",
			message="\n".join(notes),
		)
