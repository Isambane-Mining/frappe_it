# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, getdate, nowdate

# South African standard VAT rate.
VAT_RATE = 0.15

# Every imported charge line that makes up the bill's subtotal.
CHARGE_FIELDS = (
    "subscription",
    "subscription_discount",
    "calls_national",
    "entertainment_services",
    "direct_provisioning",
    "calls_international",
    "calls_roaming",
    "calls_discount",
    "calls_data",
    "calls_data_discount",
    "calls_messaging",
    "calls_messaging_discount",
    "bundles_voice",
    "bundles_messaging",
    "bundles_data",
    "bundles_adhoc",
    "clip",
    "blackberry",
    "itemised_billing",
    "vodamanage",
    "look_4_services",
    "insurance",
    "equipment",
    "connection_fee",
    "connection_fee_discount",
    "admin_fee",
    "other",
)

# Fixed monthly charges that are part of the contract, so never overspend.
CONTRACTED_FIELDS = ("subscription", "equipment", "clip", "itemised_billing", "insurance")


def calculate_bill(values):
    """Calculated totals and overspend for a bill's charge lines (a doc or dict)."""
    subtotal = sum(flt(values.get(field)) for field in CHARGE_FIELDS)
    vat = subtotal * VAT_RATE
    overspend = subtotal - sum(flt(values.get(field)) for field in CONTRACTED_FIELDS)

    return {
        "calculated_subtotal": subtotal,
        "calculated_vat": vat,
        "calculated_total": subtotal + vat,
        "overspend_amount": overspend,
        "overspend": 1 if overspend > 0 else 0,
    }


class MonthlyBill(Document):
    def before_save(self):
        self.update(calculate_bill(self))

        if not self.billing_month:
            self.billing_month = get_first_day(getdate(self.creation or nowdate()))
