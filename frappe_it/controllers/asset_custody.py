# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

"""Keep each Asset's own Custodian / Location in step with Asset Allocation.

Asset Allocation is a living document - one per holder, never submitted, rows
added and removed as kit is handed out and returned. Every save pushes the
holder onto the Assets it lists:

    Employee holder -> Asset.custodian = that Employee (location untouched)
    Location holder -> Asset.location  = that Location (custodian untouched)
    Asset holder    -> Asset.location  = the parent Asset's location

Removing a row from an Employee's allocation releases custody: the Asset's
custodian is cleared, or handed to whoever received it on an Asset Return.

How the Asset is updated depends on its docstatus:

* Draft Assets (most of the IT register, until it moves to full accounting)
  can't take an Asset Movement - ERPNext refuses to move a Draft Asset - so
  the fields are written directly and a timeline comment records why.
* Submitted Assets get a real, submitted Asset Movement referencing the
  document that caused it. ERPNext's Asset Movement is not a diff: on submit
  it applies the latest movement's target_location AND to_employee as the
  Asset's new state (custodian even when blank). Every movement here
  therefore carries the unchanged value forward, exactly as engineering's
  Vehicle Allocation does.
* Scrapped / Sold / cancelled Assets are left alone.
"""

import frappe
from frappe import _
from frappe.utils import get_link_to_form, now_datetime

UNCHANGED = object()
FROZEN_STATUSES = ("Scrapped", "Sold")


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


def sync_allocation(allocation):
	"""Push an Asset Allocation's holder onto its Assets, and release custody
	of any Asset that left an Employee holder since the last save."""
	before = allocation.get_doc_before_save()
	reference = (allocation.doctype, allocation.name)

	targets = get_holder_targets(allocation.employee_or_asset, allocation.allocated_to)
	current_assets = [row.asset for row in allocation.list_of_allocated_assets if row.asset]

	released = set()
	old_holder_type = old_holder = None
	if before:
		old_holder_type, old_holder = before.employee_or_asset, before.allocated_to
		previous_assets = {row.asset for row in before.list_of_allocated_assets if row.asset}
		holder_changed = (old_holder_type, old_holder) != (
			allocation.employee_or_asset,
			allocation.allocated_to,
		)
		# A changed holder releases every asset from the old one, not just removed rows.
		released = previous_assets if holder_changed else previous_assets - set(current_assets)

	skip_release = allocation.flags.get("frappe_it_skip_release") or set()

	for asset in dict.fromkeys(current_assets + sorted(released)):
		changes = dict(targets) if asset in current_assets else {}

		if (
			asset in released
			and asset not in skip_release
			and old_holder_type == "Employee"
			and "custodian" not in changes
			and frappe.db.get_value("Asset", asset, "custodian") == old_holder
		):
			changes["custodian"] = None

		if changes:
			apply_to_asset(asset, reference=reference, **changes)


def release_allocation(allocation):
	"""An Asset Allocation is being deleted: release custody of its Assets."""
	if allocation.employee_or_asset != "Employee":
		return

	for row in allocation.list_of_allocated_assets:
		if row.asset and frappe.db.get_value("Asset", row.asset, "custodian") == allocation.allocated_to:
			apply_to_asset(row.asset, reference=(allocation.doctype, allocation.name), custodian=None)


def apply_to_asset(asset_name, reference, custodian=UNCHANGED, location=UNCHANGED):
	"""Set an Asset's custodian and/or location; a no-op if nothing differs.

	`reference` is a (doctype, name) tuple for the document causing the change.
	A blank location is never applied - an Asset always keeps one."""
	asset = frappe.db.get_value(
		"Asset",
		asset_name,
		["name", "docstatus", "status", "custodian", "location", "company"],
		as_dict=True,
	)
	if not asset:
		return

	new_custodian = asset.custodian if custodian is UNCHANGED else (custodian or None)
	new_location = asset.location if location is UNCHANGED or not location else location

	if (new_custodian or None) == (asset.custodian or None) and new_location == asset.location:
		return

	if asset.docstatus == 0:
		_update_draft_asset(asset, new_custodian, new_location, reference)
	elif asset.docstatus == 1 and asset.status not in FROZEN_STATUSES:
		_move_submitted_asset(asset, new_custodian, new_location, reference)


def _update_draft_asset(asset, custodian, location, reference):
	frappe.db.set_value("Asset", asset.name, {"custodian": custodian, "location": location})

	changes = []
	if (custodian or None) != (asset.custodian or None):
		changes.append(_("Custodian: {0} → {1}").format(asset.custodian or "-", custodian or "-"))
	if location != asset.location:
		changes.append(_("Location: {0} → {1}").format(asset.location or "-", location or "-"))

	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Asset",
			"reference_name": asset.name,
			"content": _("{0} (Draft Asset, updated by {1})").format(
				"; ".join(changes), get_link_to_form(*reference)
			),
		}
	).insert(ignore_permissions=True)


def _move_submitted_asset(asset, custodian, location, reference):
	current_location, current_custodian = asset.location, asset.custodian

	if location != current_location:
		_create_asset_movement(
			asset,
			reference,
			purpose="Transfer",
			source_location=current_location,
			target_location=location,
			to_employee=current_custodian,  # carry forward - see module docstring
		)
		current_location = location

	if (custodian or None) != (current_custodian or None):
		if custodian:
			_create_asset_movement(
				asset,
				reference,
				purpose="Issue",
				target_location=current_location,  # carry forward
				to_employee=custodian,
			)
		else:
			# Releasing custody: a Receipt back into the same location with no
			# employee is the only movement ERPNext accepts that blanks custodian.
			_create_asset_movement(asset, reference, purpose="Receipt", target_location=current_location)


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
	from frappe.utils import nowdate

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
	the custody sync leaves the removed Assets' custodian for the caller to set."""
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
