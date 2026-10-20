# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from frappe_it.controllers.asset_custody import RETURN_LOCATION
from frappe_it.tests.factories import make_allocation, make_asset, make_employee, make_location


def _movements(reference_doctype, reference_name):
	return frappe.get_all(
		"Asset Movement",
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name, "docstatus": 1},
		fields=["name", "purpose"],
		order_by="creation asc",
	)


def _state(asset):
	custodian, location = frappe.db.get_value("Asset", asset, ["custodian", "location"])
	return custodian or None, location  # ERPNext stores a cleared custodian as ""


class RollbackEachTest(IntegrationTestCase):
	"""IntegrationTestCase only rolls back per class; these tests share names."""

	def setUp(self):
		make_location(RETURN_LOCATION)
		self.store = make_location("_Test IT Store")
		self.site = make_location("_Test IT Site")
		self.employee = make_employee("_T-IT-EMP-1")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()


class TestAllocationRules(RollbackEachTest):
	def test_draft_asset_cannot_be_allocated(self):
		draft = make_asset("_T-IT-DRAFT-1", self.store)

		with self.assertRaises(frappe.ValidationError):
			make_allocation("Employee", self.employee, [draft])

	def test_asset_cannot_be_on_two_allocations(self):
		asset = make_asset("_T-IT-SIM-1", self.store, submitted=True)
		make_allocation("Employee", self.employee, [asset])

		with self.assertRaises(frappe.ValidationError):
			make_allocation("Employee", make_employee("_T-IT-EMP-2"), [asset])

	def test_allocated_asset_cannot_be_cancelled_or_deleted(self):
		asset = make_asset("_T-IT-SIM-1", self.store, submitted=True)
		make_allocation("Employee", self.employee, [asset])

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc("Asset", asset).cancel()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Asset", asset, ignore_permissions=True)


class TestAllocationMovements(RollbackEachTest):
	def setUp(self):
		super().setUp()
		self.asset = make_asset("_T-IT-SIM-1", self.store, submitted=True)

	def test_employee_allocation_issues_and_keeps_location(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])

		self.assertEqual([m.purpose for m in _movements("Asset Allocation", allocation.name)], ["Issue"])
		self.assertEqual(_state(self.asset), (self.employee, self.store))

	def test_location_allocation_transfers_and_keeps_custodian(self):
		frappe.db.set_value("Asset", self.asset, "custodian", self.employee)

		allocation = make_allocation("Location", self.site, [self.asset], site=self.site)

		self.assertEqual([m.purpose for m in _movements("Asset Allocation", allocation.name)], ["Transfer"])
		self.assertEqual(_state(self.asset), (self.employee, self.site))

	def test_removing_from_employee_returns_to_it(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])
		allocation.list_of_allocated_assets = []
		allocation.save(ignore_permissions=True)

		self.assertEqual(_state(self.asset), (None, RETURN_LOCATION))
		self.assertEqual(
			[m.purpose for m in _movements("Asset Allocation", allocation.name)], ["Issue", "Transfer"]
		)

	def test_removing_from_location_returns_to_it(self):
		allocation = make_allocation("Location", self.site, [self.asset], site=self.site)
		allocation.list_of_allocated_assets = []
		allocation.save(ignore_permissions=True)

		self.assertEqual(_state(self.asset), (None, RETURN_LOCATION))

	def test_already_at_store_only_releases_custody(self):
		frappe.db.set_value("Asset", self.asset, "location", RETURN_LOCATION)
		allocation = make_allocation("Employee", self.employee, [self.asset])
		allocation.list_of_allocated_assets = []
		allocation.save(ignore_permissions=True)

		self.assertEqual(_state(self.asset), (None, RETURN_LOCATION))
		self.assertEqual(
			[m.purpose for m in _movements("Asset Allocation", allocation.name)], ["Issue", "Receipt"]
		)

	def test_resaving_is_a_no_op(self):
		allocation = make_allocation("Employee", self.employee, [self.asset])
		allocation.save(ignore_permissions=True)

		self.assertEqual(len(_movements("Asset Allocation", allocation.name)), 1)


class TestAssetReturn(RollbackEachTest):
	def setUp(self):
		super().setUp()
		self.receiver = make_employee("_T-IT-RECEIVER")
		self.asset = make_asset("_T-IT-PHONE-1", self.store, submitted=True)
		self.allocation = make_allocation("Employee", self.employee, [self.asset])

	def test_return_sends_to_it_and_cancel_restores(self):
		asset_return = frappe.new_doc("Asset Return")
		asset_return.employee = self.employee
		asset_return.receiver = self.receiver
		asset_return.attach_signed = "/files/_test_signed.pdf"
		asset_return.append(
			"list_of_allocated_assets", {"asset": self.asset, "check_in_date": frappe.utils.nowdate()}
		)
		asset_return.insert(ignore_permissions=True)
		asset_return.submit()

		self.assertEqual(_state(self.asset), (None, RETURN_LOCATION))
		self.assertEqual([m.purpose for m in _movements("Asset Return", asset_return.name)], ["Transfer"])
		self.allocation.reload()
		self.assertFalse(self.allocation.list_of_allocated_assets)

		asset_return.cancel()

		self.assertEqual(_state(self.asset), (self.employee, self.store))
		self.allocation.reload()
		self.assertEqual([r.asset for r in self.allocation.list_of_allocated_assets], [self.asset])
