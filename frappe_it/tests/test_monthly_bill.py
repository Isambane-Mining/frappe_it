# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

from frappe.tests import UnitTestCase

from frappe_it.frappe_it.doctype.monthly_bill.monthly_bill import calculate_bill


class TestMonthlyBillCalculation(UnitTestCase):
	def test_contracted_charges_are_not_overspend(self):
		totals = calculate_bill(
			{
				"subscription": 300,
				"equipment": 200,
				"clip": 10,
				"itemised_billing": 5,
				"insurance": 50,
			}
		)
		self.assertEqual(totals["calculated_subtotal"], 565)
		self.assertEqual(totals["overspend_amount"], 0)
		self.assertEqual(totals["overspend"], 0)

	def test_usage_is_overspend_and_vat_applies(self):
		totals = calculate_bill({"subscription": 300, "calls_data": 120, "calls_roaming": None})
		self.assertEqual(totals["overspend_amount"], 120)
		self.assertEqual(totals["overspend"], 1)
		self.assertAlmostEqual(totals["calculated_vat"], 63)
		self.assertAlmostEqual(totals["calculated_total"], 483)
