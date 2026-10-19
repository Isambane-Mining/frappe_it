# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_months, getdate


def execute(filters=None):
    columns = [
        {"label": _("SIM Number"), "fieldname": "sim_no", "fieldtype": "Link", "options": "Simcard Allocations", "width": 205},
        {"label": _("Telephone Number"), "fieldname": "tel_no", "fieldtype": "Phone", "width": 145},
        {"label": _("Allocated To Type"), "fieldname": "employee_or_site", "fieldtype": "Link", "options": "DocType", "hidden": 1},
        {"label": _("Allocated To"), "fieldname": "allocated_to", "fieldtype": "Dynamic Link", "options": "employee_or_site", "width": 120},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": _("Notes"), "fieldname": "notes", "fieldtype": "Small Text", "width": 200},
        {"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 120},
        {"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 120},
    ]

    # Contracts already expired or expiring within the next three months
    data = frappe.db.sql(
        """
        select
            s.sim_no,
            s.tel_no,
            s.employee_or_site,
            s.allocated_to,
            s.employee_name,
            s.notes,
            s.start_date,
            s.end_date
        from `tabSimcard Allocations` s
        where s.end_date <= %(three_months_later)s
        order by s.end_date
        """,
        {"three_months_later": add_months(getdate(), 3)},
        as_dict=True,
    )

    return columns, data
