"""Create the IT Item Groups under this site's root Item Group.

These used to be a fixture with parent "All Item Groups", but that root is
only created by ERPNext's setup wizard (and is translated), so installing
frappe_it on a site that hadn't completed setup crashed in the nested-set
update. Runs after install and after every migrate; existing Item Groups are
never touched.
"""

import frappe
from frappe.utils.nestedset import get_root_of

ITEM_GROUPS = (
	"Cellphone Simcards",
	"Handheld Radio",
	"IP Cameras",
	"NVRs",
	"Vehicle Mounted Radio",
	"Cellular Telephone",
	"Laptop Computer",
)


def ensure_item_groups():
	if not frappe.db.table_exists("Item Group"):
		return

	missing = [name for name in ITEM_GROUPS if not frappe.db.exists("Item Group", name)]
	if not missing:
		return

	root = get_root_of("Item Group")
	if not root:
		# ERPNext setup wizard not completed yet; the next migrate tries again.
		frappe.logger("frappe_it").info(
			"Item Groups %s not created: no root Item Group yet.", ", ".join(missing)
		)
		return

	for name in missing:
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": root,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
