# Copyright (c) 2025, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from frappe_it.controllers.asset_custody import (
	add_assets_to_allocation,
	apply_to_asset,
	cancel_asset_movements,
	find_allocations,
	remove_assets_from_allocations,
)


class AssetReturn(Document):
	def before_submit(self):
		if not self.attach_signed:
			frappe.throw(_("Please attach a signed copy before submitting."))
		self.warn_about_unallocated_assets()

	def warn_about_unallocated_assets(self):
		allocated = set(
			frappe.get_all(
				"Asset Allocation Table",
				filters={"parenttype": "Asset Allocation", "parent": ["in", find_allocations("Employee", self.employee) or [""]]},
				pluck="asset",
			)
		)
		missing = [row.asset for row in self.list_of_allocated_assets if row.asset and row.asset not in allocated]
		if missing:
			frappe.msgprint(
				_("These assets were not on {0}'s Asset Allocation, but are being returned anyway: {1}").format(
					self.employee_name or self.employee, ", ".join(missing)
				),
				indicator="orange",
				alert=True,
			)

	def on_submit(self):
		"""The returned assets leave the employee's allocation and the
		receiver becomes their custodian."""
		assets = self._assets()
		remove_assets_from_allocations("Employee", self.employee, assets, skip_release=True)
		for asset in assets:
			apply_to_asset(asset, reference=(self.doctype, self.name), custodian=self.receiver)

	def on_cancel(self):
		"""Undo the return: reverse its Asset Movements and put the assets back
		on the employee's allocation."""
		cancel_asset_movements(self.doctype, self.name)

		rows = {row.asset: row for row in self.list_of_allocated_assets if row.asset}
		if rows:
			add_assets_to_allocation(
				"Employee",
				self.employee,
				"Branch",
				self.branch,
				list(rows),
				note=_("Restored by cancelling Asset Return {0}").format(self.name),
			)

	def _assets(self):
		return list(dict.fromkeys(row.asset for row in self.list_of_allocated_assets if row.asset))
