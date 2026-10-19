"""Superseded: the IT Asset Categories and Item Groups are created (and
re-checked after every migrate) by frappe_it.setup.asset_categories and
frappe_it.setup.item_groups, which cope with sites that have no default
company or chart of accounts yet. Kept so the Patch Log entry still resolves."""

from frappe_it.setup.asset_categories import ensure_asset_categories
from frappe_it.setup.item_groups import ensure_item_groups


def execute():
	ensure_item_groups()
	ensure_asset_categories()
