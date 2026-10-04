"""Create the IT Asset Categories against this site's own accounts.

These used to be a fixture, but the fixture carried Isambane/Excavo account
names ("Softwares - ISA", "Electronic Equipments - ISA" ...), so installing
frappe_it on any site with a different chart of accounts failed. frappe_it
only relies on the category names; the accounts are company accounting data.

Runs after install and after every migrate. Existing categories are never
touched, so sites that already have them (prod) keep their own accounts.
"""

import frappe

# category -> (preferred Fixed Asset ledger name prefix, non_depreciable_category)
# Prefixes match both ERPNext's standard chart and za_local's SA chart.
ASSET_CATEGORIES = {
	"Software Licence": ("Software", 1),
	"IP Cameras": ("Electronic Equipment", 0),
	"NVRs": ("Electronic Equipment", 0),
	"Handheld Radio": ("Electronic Equipment", 0),
	"Vehicle Mounted Radio": ("Electronic Equipment", 0),
	"Cellphone Simcards": ("Electronic Equipment", 0),
	"Laptop Computer": ("Electronic Equipment", 0),
	"Cellular Telephone": ("Electronic Equipment", 0),
	"Computer Monitor": ("Electronic Equipment", 0),
}


def ensure_asset_categories():
	if not frappe.db.table_exists("Asset Category"):
		return

	missing = [name for name in ASSET_CATEGORIES if not frappe.db.exists("Asset Category", name)]
	if not missing:
		return

	company = _get_default_company()
	created = []
	for name in missing:
		account_prefix, non_depreciable = ASSET_CATEGORIES[name]
		account_row = company and _get_account_row(company, account_prefix)
		if not account_row:
			continue

		frappe.get_doc(
			{
				"doctype": "Asset Category",
				"asset_category_name": name,
				"non_depreciable_category": non_depreciable,
				"accounts": [account_row],
			}
		).insert(ignore_permissions=True)
		created.append(name)

	skipped = [name for name in missing if name not in created]
	if skipped:
		# No company / chart of accounts yet (e.g. before the setup wizard).
		# The next migrate tries again.
		frappe.logger("frappe_it").info(
			"Asset Categories %s not created: no default company with a Fixed Asset account yet.",
			", ".join(skipped),
		)


def _get_default_company() -> str | None:
	return frappe.defaults.get_global_default("company") or frappe.db.get_value(
		"Company", {}, "name", order_by="creation asc"
	)


def _get_account_row(company: str, account_prefix: str) -> dict | None:
	filters = {"company": company, "account_type": "Fixed Asset", "is_group": 0, "disabled": 0}
	# Prefer the matching standard ledger, else the company's first Fixed Asset ledger.
	fixed_asset_account = frappe.db.get_value(
		"Account", {**filters, "account_name": ["like", f"{account_prefix}%"]}, "name", order_by="lft asc"
	) or frappe.db.get_value("Account", filters, "name", order_by="lft asc")
	if not fixed_asset_account:
		return None

	defaults = frappe.db.get_value(
		"Company",
		company,
		["accumulated_depreciation_account", "depreciation_expense_account"],
		as_dict=True,
	)

	return {
		"company_name": company,
		"fixed_asset_account": fixed_asset_account,
		"accumulated_depreciation_account": defaults.accumulated_depreciation_account,
		"depreciation_expense_account": defaults.depreciation_expense_account,
	}
