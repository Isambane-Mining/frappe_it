"""Bring every allocated Asset's own Custodian / Location in line with its
current Asset Allocation, the same way saving the allocation now does
(Draft Assets updated in place, submitted ones through an Asset Movement).

An Asset listed on more than one Asset Allocation is skipped - there is no
single right holder to apply - and logged, as is any Asset ERPNext refuses
to move (for example an Employee from another company). Fix those by hand
and re-save the allocation.
"""

import frappe

from frappe_it.controllers.asset_custody import apply_to_asset, get_holder_targets


def execute():
	rows = frappe.get_all(
		"Asset Allocation Table",
		filters={"parenttype": "Asset Allocation"},
		fields=["asset", "parent"],
	)

	parents_by_asset = {}
	for row in rows:
		if row.asset:
			parents_by_asset.setdefault(row.asset, set()).add(row.parent)

	problems = []
	targets_by_allocation = {}

	for asset, parents in sorted(parents_by_asset.items()):
		if len(parents) > 1:
			problems.append(f"{asset}: on more than one Asset Allocation ({', '.join(sorted(parents))}) - skipped")
			continue

		(allocation,) = parents
		if allocation not in targets_by_allocation:
			holder_type, holder = frappe.db.get_value(
				"Asset Allocation", allocation, ["employee_or_asset", "allocated_to"]
			)
			targets_by_allocation[allocation] = get_holder_targets(holder_type, holder)

		targets = targets_by_allocation[allocation]
		if not targets:
			continue

		frappe.db.savepoint("frappe_it_custody")
		try:
			apply_to_asset(asset, reference=("Asset Allocation", allocation), **targets)
		except Exception as e:
			frappe.db.rollback(save_point="frappe_it_custody")
			frappe.clear_messages()
			problems.append(f"{asset} ({allocation}): {e}")

	if problems:
		frappe.log_error(
			title="frappe_it: Asset custody backfill skipped assets",
			message="\n".join(problems),
		)
