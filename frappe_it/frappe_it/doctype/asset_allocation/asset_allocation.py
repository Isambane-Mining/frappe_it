# Copyright (c) 2025, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

from frappe_it.controllers.asset_custody import is_allocatable, release_allocation, sync_allocation


class AssetAllocation(Document):
	def validate(self):
		self.validate_assets()

	def validate_assets(self):
		seen = set()
		for row in self.list_of_allocated_assets:
			if not row.asset:
				continue
			if row.asset in seen:
				frappe.throw(_("Row #{0}: Asset {1} is listed more than once.").format(row.idx, row.asset))
			if self.employee_or_asset == "Asset" and row.asset == self.allocated_to:
				frappe.throw(_("Row #{0}: An Asset can't be allocated to itself.").format(row.idx))
			seen.add(row.asset)

		# Only newly added rows are checked against other allocations, so a
		# legacy clash doesn't block unrelated edits to either document.
		before = self.get_doc_before_save()
		previous = {row.asset for row in before.list_of_allocated_assets} if before else set()
		added = seen - previous
		if not added:
			return

		not_submitted = sorted(asset for asset in added if not is_allocatable(asset))
		if not_submitted:
			frappe.throw(
				_("Only submitted Assets can be allocated: {0}").format(", ".join(not_submitted)),
				title=_("Asset Not Submitted"),
			)

		clashes = frappe.get_all(
			"Asset Allocation Table",
			filters={
				"asset": ["in", list(added)],
				"parenttype": "Asset Allocation",
				"parent": ["!=", self.name],
			},
			fields=["asset", "parent"],
		)
		if clashes:
			frappe.throw(
				"<br>".join(
					_("Asset {0} is already allocated in {1}.").format(
						c.asset, get_link_to_form("Asset Allocation", c.parent)
					)
					for c in clashes
				),
				title=_("Asset Already Allocated"),
			)

	def on_update(self):
		sync_allocation(self)

	def on_trash(self):
		release_allocation(self)


@frappe.whitelist()
def check_asset_allocation(asset, docname=None):
	"""Check if an asset is already allocated in another 'Asset Allocation' document."""
	if not frappe.has_permission("Asset Allocation", "read"):
		frappe.throw(_("You do not have permission to access this resource."), frappe.PermissionError)

	return frappe.get_all(
		"Asset Allocation Table",
		filters={"asset": asset, "parenttype": "Asset Allocation", "parent": ["!=", docname]},
		pluck="parent",
	)
