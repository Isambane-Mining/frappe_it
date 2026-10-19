# Copyright (c) 2025, buff0k and contributors
# For license information, please see license.txt

from frappe_it.setup.doclinks import ensure_links


def ensure_asset_links():
    """Show Simcard Allocations and Asset Allocations on the Asset form's Connections."""
    ensure_links(
        "Asset",
        [
            {"link_doctype": "Simcard Allocations", "link_fieldname": "sim_no"},
            {
                "link_doctype": "Asset Allocation Table",
                "link_fieldname": "asset",
                "parent_doctype": "Asset Allocation",
                "table_fieldname": "list_of_allocated_assets",
                "is_child_table": 1,
            },
        ],
    )
