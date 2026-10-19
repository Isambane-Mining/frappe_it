# Copyright (c) 2025, buff0k and contributors
# For license information, please see license.txt

from frappe_it.setup.doclinks import ensure_links


def ensure_employee_links():
    """Show Asset Allocations and Simcard Allocations on the Employee form's Connections."""
    ensure_links(
        "Employee",
        [
            {"link_doctype": "Asset Allocation", "link_fieldname": "allocated_to"},
            {"link_doctype": "Simcard Allocations", "link_fieldname": "allocated_to"},
        ],
    )
