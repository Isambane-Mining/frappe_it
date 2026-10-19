# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, getdate


def execute(filters=None):
    filters = filters or {}

    if not filters.get("month"):
        frappe.throw(_("Please select a month to run the report."))

    columns = [
        {"label": _("Monthly Bill"), "fieldname": "name", "fieldtype": "Link", "options": "Monthly Bill", "width": 100},
        {"label": _("Billing Month"), "fieldname": "billing_month", "fieldtype": "Date", "width": 110},
        {"label": _("SIM Card No"), "fieldname": "sim_card_no", "fieldtype": "Link", "options": "Simcard Allocations", "width": 205},
        {"label": _("Telephone Number"), "fieldname": "tel_no", "fieldtype": "Data", "width": 145},
        {"label": _("Allocated To Type"), "fieldname": "employee_or_site", "fieldtype": "Link", "options": "DocType", "hidden": 1},
        {"label": _("Allocated To"), "fieldname": "allocated_to", "fieldtype": "Dynamic Link", "options": "employee_or_site", "width": 120},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": _("Notes"), "fieldname": "notes", "fieldtype": "Small Text", "width": 250},
        {"label": _("Overspend Amount"), "fieldname": "overspend_amount", "fieldtype": "Currency", "width": 120},
    ]

    month = getdate(filters.get("month"))

    data = frappe.db.sql(
        """
        select
            b.name,
            b.billing_month,
            b.sim_card_no,
            s.tel_no,
            s.employee_or_site,
            s.allocated_to,
            s.employee_name,
            s.notes,
            b.overspend_amount
        from `tabMonthly Bill` b
        left join `tabSimcard Allocations` s on b.sim_card_no = s.name
        where b.overspend = 1
            and b.billing_month between %(from_date)s and %(to_date)s
        order by b.overspend_amount desc
        """,
        {"from_date": get_first_day(month), "to_date": get_last_day(month)},
        as_dict=True,
    )

    return columns, data
