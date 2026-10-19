# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from frappe_it.tests.factories import make_allocation, make_asset, make_employee, make_location


def _movements(reference_doctype, reference_name):
	return frappe.get_all(
		"Asset Movement",
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name, "docstatus": 1},
		fields=["name", "purpose"],
		order_by="creation asc",
	)


class RollbackEachTest(IntegrationTestCase):
	"""IntegrationTestCase only rolls back per class; these tests share names."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()


class TestDraftAssetCustody(RollbackEachTest):
	def setUp(self):
		self.store = make_location("_Test IT Store")
		self.site = make_location("_Test IT Site")
		self.employee = make_employee("_T-IT-EMP-1")
		self.asset = make_asset("_T-IT-LAPTOP-1", self.store)

	def test_employee_allocation_sets_custodian_with_comment(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])

		self.assertEqual(frappe.db.get_value("Asset", self.asset, "custodian"), self.employee)
		self.assertEqual(frappe.db.get_value("Asset", self.asset, "location"), self.store)
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "Asset", "reference_name": self.asset, "comment_type": "Info"},
			)
		)
		self.assertFalse(_movements("Asset Allocation", allocation.name))

	def test_removing_row_releases_custody(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])
		allocation.list_of_allocated_assets = []
		allocation.save(ignore_permissions=True)

		self.assertIsNone(frappe.db.get_value("Asset", self.asset, "custodian"))

	def test_location_allocation_moves_asset_only(self):
		frappe.db.set_value("Asset", self.asset, "custodian", self.employee)
		make_allocation("Location", self.site, [self.asset], site=self.site)

		self.assertEqual(frappe.db.get_value("Asset", self.asset, "location"), self.site)
		self.assertEqual(frappe.db.get_value("Asset", self.asset, "custodian"), self.employee)

	def test_asset_cannot_be_on_two_allocations(self):
		make_allocation("Employee", self.employee, [self.asset])
		other = make_employee("_T-IT-EMP-2")

		with self.assertRaises(frappe.ValidationError):
			make_allocation("Employee", other, [self.asset])

	def test_resaving_is_a_no_op(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])
		comments = frappe.db.count("Comment", {"reference_doctype": "Asset", "reference_name": self.asset})

		allocation.save(ignore_permissions=True)

		self.assertEqual(
			frappe.db.count("Comment", {"reference_doctype": "Asset", "reference_name": self.asset}), comments
		)


class TestSubmittedAssetCustody(RollbackEachTest):
	def setUp(self):
		self.store = make_location("_Test IT Store")
		self.site = make_location("_Test IT Site")
		self.employee = make_employee("_T-IT-EMP-1")
		self.asset = make_asset("_T-IT-SIM-1", self.store, submitted=True)

	def test_employee_allocation_issues_through_asset_movement(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])

		movements = _movements("Asset Allocation", allocation.name)
		self.assertEqual([m.purpose for m in movements], ["Issue"])
		item = frappe.get_all(
			"Asset Movement Item", filters={"parent": movements[0].name}, fields=["target_location", "to_employee"]
		)[0]
		self.assertEqual(item.to_employee, self.employee)
		self.assertEqual(item.target_location, self.store)  # carried forward
		self.assertEqual(frappe.db.get_value("Asset", self.asset, "custodian"), self.employee)

	def test_location_allocation_transfers_and_keeps_custodian(self):
		frappe.db.set_value("Asset", self.asset, "custodian", self.employee)

		allocation = make_allocation("Location", self.site, [self.asset], site=self.site)

		self.assertEqual([m.purpose for m in _movements("Asset Allocation", allocation.name)], ["Transfer"])
		self.assertEqual(frappe.db.get_value("Asset", self.asset, "location"), self.site)
		self.assertEqual(frappe.db.get_value("Asset", self.asset, "custodian"), self.employee)


class TestAssetReturnCustody(RollbackEachTest):
	def setUp(self):
		self.store = make_location("_Test IT Store")
		self.employee = make_employee("_T-IT-EMP-1")
		self.receiver = make_employee("_T-IT-RECEIVER")
		self.asset = make_asset("_T-IT-PHONE-1", self.store)
		self.allocation = make_allocation("Employee", self.employee, [self.asset])

	def _make_return(self):
		doc = frappe.new_doc("Asset Return")
		doc.employee = self.employee
		doc.receiver = self.receiver
		doc.attach_signed = "/files/_test_signed.pdf"
		doc.append("list_of_allocated_assets", {"asset": self.asset, "check_in_date": frappe.utils.nowdate()})
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc

	def test_return_moves_custody_to_receiver_and_cancel_restores(self):
		asset_return = self._make_return()

		self.assertEqual(frappe.db.get_value("Asset", self.asset, "custodian"), self.receiver)
		self.allocation.reload()
		self.assertFalse(self.allocation.list_of_allocated_assets)

		asset_return.cancel()

		self.assertEqual(frappe.db.get_value("Asset", self.asset, "custodian"), self.employee)
		self.allocation.reload()
		self.assertEqual([r.asset for r in self.allocation.list_of_allocated_assets], [self.asset])
