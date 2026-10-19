"""Monthly Bill overspend now follows one formula (subscription, equipment,
CLIP, itemised billing and insurance are contracted, never overspend) and
bills carry a Billing Month for the Overspend Monthly Report. Recalculate
every stored bill and default Billing Month to the month it was created.
"""

import frappe
from frappe.utils import get_first_day

from frappe_it.frappe_it.doctype.monthly_bill.monthly_bill import CHARGE_FIELDS, calculate_bill


def execute():
	for bill in frappe.get_all("Monthly Bill", fields=["name", "creation", "billing_month", *CHARGE_FIELDS]):
		values = calculate_bill(bill)
		if not bill.billing_month:
			values["billing_month"] = get_first_day(bill.creation)
		frappe.db.set_value("Monthly Bill", bill.name, values, update_modified=False)
