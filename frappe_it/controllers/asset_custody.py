# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Keep each Asset's own Custodian / Location in step with Asset Allocation.

Asset Allocation is a living document - one per holder, never submitted, rows
added and removed as kit is handed out and returned. Only submitted Assets can
be allocated. Every save pushes the holder onto the Assets it lists through a
real, submitted Asset Movement referencing the document that caused it:

    Employee holder -> custodian = that Employee (location untouched)
    Location holder -> location  = that Location (custodian untouched)
    Asset holder    -> location  = the parent Asset's location

An Asset that leaves an allocation (row removed, holder changed, allocation
deleted, Asset Return) goes back to IT: no custodian, location RETURN_LOCATION.

ERPNext's Asset Movement is not a diff: on submit it applies the latest
movement's target_location AND to_employee as the Asset's new state (custodian
even when blank). Every movement here therefore states the complete intended
state, as engineering's Vehicle Allocation does.
"""

import frappe
from frappe import _
from frappe.utils import get_link_to_form, now_datetime, nowdate

# Where IT keeps unallocated kit.
RETURN_LOCATION = "Plot 22"

UNCHANGED = object()
FROZEN_STATUSES = ("Scrapped", "Sold")


def is_allocatable(asset_name):
	docstatus, status = frappe.db.get_value("Asset", asset_name, ["docstatus", "status"]) or (None, None)
	return docstatus == 1 and status not in FROZEN_STATUSES


def get_holder_targets(holder_type, holder):
	"""What allocating to this holder means for an Asset's own fields."""
	if not holder_type or not holder:
		return {}

	if holder_type == "Employee":
		return {"custodian": holder}

	if holder_type == "Location":
		return {"location": holder}

	if holder_type == "Asset":
		location = frappe.db.get_value("Asset", holder, "location")
		return {"location": location} if location else {}

	return {}


def return_targets():
	if not frappe.db.exists("Location", RETURN_LOCATION):
		frappe.throw(
			_("Location {0} (where returned IT assets go) does not exist.").format(frappe.bold(RETURN_LOCATION))
		)
	return {"custodian": None, "location": RETURN_LOCATION}


def sync_allocation(allocation):
	"""Push an Asset Allocation's holder onto its Assets, and send any Asset
	that left it since the last save back to IT."""
	before = allocation.get_doc_before_save()
	reference = (allocation.doctype, allocation.name)

	targets = get_holder_targets(allocation.employee_or_asset, allocation.allocated_to)
	current_assets = [row.asset for row in allocation.list_of_allocated_assets if row.asset]

	previous_assets, holder_changed, old_holder_type = set(), False, None
	if before:
		old_holder_type = before.employee_or_asset
		previous_assets = {row.asset for row in before.list_of_allocated_assets if row.asset}
		holder_changed = (before.employee_or_asset, before.allocated_to) != (
			allocation.employee_or_asset,
			allocation.allocated_to,
		)

	for asset in current_assets:
		changes = dict(targets)
		# Moved off an Employee onto a Location / Asset: nobody holds it any more.
		if holder_changed and old_holder_type == "Employee" and "custodian" not in changes:
			changes["custodian"] = None
		apply_to_asset(asset, reference=reference, **changes)

	skip_release = allocation.flags.get("frappe_it_skip_release") or set()
	for asset in sorted(previous_assets - set(current_assets) - set(skip_release)):
		apply_to_asset(asset, reference=reference, **return_targets())


def release_allocation(allocation):
	"""An Asset Allocation is being deleted: its Assets go back to IT."""
	for row in allocation.list_of_allocated_assets:
		if row.asset:
			apply_to_asset(row.asset, reference=(allocation.doctype, allocation.name), **return_targets())


def apply_to_asset(asset_name, reference, custodian=UNCHANGED, location=UNCHANGED):
	"""Move a submitted Asset to this custodian and/or location with one Asset
	Movement; a no-op if nothing differs. Draft, Scrapped and Sold Assets are
	left alone. `reference` is the (doctype, name) causing the change."""
	asset = frappe.db.get_value(
		"Asset",
		asset_name,
		["name", "docstatus", "status", "custodian", "location", "company"],
		as_dict=True,
	)
	if not asset or asset.docstatus != 1 or asset.status in FROZEN_STATUSES:
		return

	new_custodian = (asset.custodian if custodian is UNCHANGED else custodian) or None
	new_location = asset.location if location is UNCHANGED or not location else location

	if new_custodian == (asset.custodian or None) and new_location == asset.location:
		return

	if new_location != asset.location:
		# A Transfer applies its to_employee too, so one movement covers both.
		purpose, source_location = "Transfer", asset.location
	elif new_custodian:
		purpose, source_location = "Issue", None
	else:
		# Same location, custody released: a Receipt with no employee is the
		# only movement ERPNext accepts that blanks the custodian.
		purpose, source_location = "Receipt", None

	_create_asset_movement(
		asset,
		reference,
		purpose=purpose,
		source_location=source_location,
		target_location=new_location,
		to_employee=new_custodian,
	)


def _create_asset_movement(asset, reference, purpose, source_location=None, target_location=None, to_employee=None):
	movement = frappe.new_doc("Asset Movement")
	movement.purpose = purpose
	movement.company = asset.company
	movement.transaction_date = now_datetime()
	movement.reference_doctype, movement.reference_name = reference
	movement.append(
		"assets",
		{
			"asset": asset.name,
			"source_location": source_location,
			"target_location": target_location,
			"to_employee": to_employee,
		},
	)
	movement.insert(ignore_permissions=True)
	movement.submit()
	return movement.name


def cancel_asset_movements(reference_doctype, reference_name):
	"""Cancel every submitted Asset Movement a document raised, newest first,
	so ERPNext restores each Asset's previous location and custodian."""
	for name in frappe.get_all(
		"Asset Movement",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"docstatus": 1,
		},
		order_by="transaction_date desc, creation desc",
		pluck="name",
	):
		movement = frappe.get_doc("Asset Movement", name)
		movement.flags.ignore_permissions = True
		movement.cancel()


def find_allocations(holder_type, holder):
	return frappe.get_all(
		"Asset Allocation",
		filters={"employee_or_asset": holder_type, "allocated_to": holder},
		pluck="name",
	)


def add_assets_to_allocation(holder_type, holder, site_type, site, assets, note=None, check_out_date=None):
	"""Append Assets to the holder's Asset Allocation, creating it if needed.
	Saving runs the normal validation and custody sync."""
	existing = find_allocations(holder_type, holder)
	if existing:
		doc = frappe.get_doc("Asset Allocation", existing[0])
	else:
		doc = frappe.new_doc("Asset Allocation")
		doc.employee_or_asset = holder_type
		doc.allocated_to = holder
		doc.branch_or_location = site_type
		doc.site = site
		if holder_type == "Employee":
			doc.employee_asset_name = frappe.db.get_value("Employee", holder, "employee_name")
		elif holder_type == "Asset":
			doc.employee_asset_name = frappe.db.get_value("Asset", holder, "item_name") or holder
		else:
			doc.employee_asset_name = holder

	already = {row.asset for row in doc.list_of_allocated_assets}
	added = False
	for asset in assets:
		if asset in already:
			continue
		doc.append(
			"list_of_allocated_assets",
			{
				"asset": asset,
				"asset_name": frappe.db.get_value("Asset", asset, "asset_name"),
				"check_out_date": check_out_date or nowdate(),
				"notes": note,
			},
		)
		added = True

	if added or doc.is_new():
		doc.save(ignore_permissions=True)
	return doc


def remove_assets_from_allocations(holder_type, holder, assets, skip_release=False):
	"""Drop Assets from every Asset Allocation of this holder. With skip_release
	the removed Assets are not sent back to IT - the caller moves them."""
	assets = set(assets)
	for name in find_allocations(holder_type, holder):
		doc = frappe.get_doc("Asset Allocation", name)
		keep = [row for row in doc.list_of_allocated_assets if row.asset not in assets]
		if len(keep) == len(doc.list_of_allocated_assets):
			continue
		doc.list_of_allocated_assets = keep
		if skip_release:
			doc.flags.frappe_it_skip_release = assets
		doc.save(ignore_permissions=True)


def block_if_allocated(doc, method=None):
	"""Asset before_cancel / on_trash: an Asset still on an Asset Allocation
	must be removed from it (or returned) first."""
	allocations = frappe.get_all(
		"Asset Allocation Table",
		filters={"asset": doc.name, "parenttype": "Asset Allocation"},
		pluck="parent",
		distinct=True,
	)
	if allocations:
		frappe.throw(
			_("Asset {0} is still allocated in {1}. Remove it from the allocation (or return it) first.").format(
				frappe.bold(doc.name),
				", ".join(get_link_to_form("Asset Allocation", name) for name in allocations),
			),
			title=_("Asset Is Allocated"),
		)
