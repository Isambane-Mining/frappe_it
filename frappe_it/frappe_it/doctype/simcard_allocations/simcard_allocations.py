# Copyright (c) 2026, BuFf0k
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, escape_html, get_url_to_form

from frappe_it.controllers.asset_custody import add_assets_to_allocation, remove_assets_from_allocations


class SimcardAllocations(Document):
    def on_update(self):
        self.update_asset_allocations()

    def update_asset_allocations(self):
        """Mirror this SIM onto the holder's Asset Allocation (which in turn
        updates the SIM Asset's custodian / location)."""
        if not self.sim_no:
            return

        if not self.employee_or_site or not self.allocated_to:
            frappe.throw(_("Allocated To and its type must be set."))
        if not self.branch_or_location or not self.site:
            frappe.throw(_("Site and its type must be set."))
        if not frappe.db.exists(self.employee_or_site, self.allocated_to):
            frappe.throw(_("{0} '{1}' does not exist.").format(self.employee_or_site, self.allocated_to))
        if not frappe.db.exists(self.branch_or_location, self.site):
            frappe.throw(_("{0} '{1}' does not exist.").format(self.branch_or_location, self.site))

        previous_doc = self.get_doc_before_save()
        if previous_doc and (
            previous_doc.employee_or_site != self.employee_or_site
            or previous_doc.allocated_to != self.allocated_to
        ):
            # Moving to another Employee sets the custodian anyway; only a move
            # to a Location needs the old Employee's custody released.
            remove_assets_from_allocations(
                previous_doc.employee_or_site,
                previous_doc.allocated_to,
                [self.sim_no],
                skip_release=self.employee_or_site == "Employee",
            )

        add_assets_to_allocation(
            self.employee_or_site,
            self.allocated_to,
            self.branch_or_location,
            self.site,
            [self.sim_no],
            note=_("Linked via Simcard Allocation {0}").format(self.name),
        )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_simcards(doctype, txt, searchfield, start, page_len, filters):
    """Link query for sim_no: submitted SIM card Assets not yet on a Simcard Allocation.
    Searches name and asset_name only - the client-supplied searchfield is
    deliberately never used in the query."""
    if not frappe.has_permission("Asset", "select"):
        return []

    asset = frappe.qb.DocType("Asset")
    allocation = frappe.qb.DocType("Simcard Allocations")
    allocated = frappe.qb.from_(allocation).select(allocation.sim_no).where(allocation.sim_no.isnotnull())
    pattern = f"%{txt}%"

    return (
        frappe.qb.from_(asset)
        .select(asset.name, asset.asset_name)
        .where(asset.asset_category == "Cellphone Simcards")
        .where(asset.docstatus == 1)
        .where(asset.status.notin(["Scrapped", "Sold"]))
        .where(asset.name.notin(allocated))
        .where(asset.name.like(pattern) | asset.asset_name.like(pattern))
        .limit(cint(page_len) or 20)
        .offset(cint(start))
        .run()
    )


@frappe.whitelist()
def get_linked_bills_html(simcard_alloc_name: str) -> str:
    """
    Render linked Monthly Bill records as a table (list view with columns).
    Colour coding:
      - overspend_amount > 0 => red (text-danger)
      - overspend_amount <= 0 or None => green (text-success)
    """
    if not simcard_alloc_name or simcard_alloc_name.startswith("new-"):
        return """
        <div class="it-linked-panel">
          <div class="it-linked-panel__empty">
            Linked bills will appear here once the record is saved.
          </div>
        </div>
        """

    doc = frappe.get_doc("Simcard Allocations", simcard_alloc_name)
    doc.check_permission("read")
    if not doc.msisdn:
        return """
        <div class="it-linked-panel">
          <div class="it-linked-panel__empty">Set an MSISDN number to show linked bills.</div>
        </div>
        """

    bills = frappe.get_list(
        "Monthly Bill",
        filters={"msisdn_no": doc.msisdn},
        fields=["name", "total", "overspend_amount"],
        order_by="modified desc",
    ) or []

    if not bills:
        return """
        <div class="it-linked-panel">
          <div class="it-linked-panel__empty">No linked bills found.</div>
        </div>
        """

    rows_html = []
    for b in bills:
        url = get_url_to_form("Monthly Bill", b.name)

        overspend = b.overspend_amount
        overspend_class = "text-success"
        if overspend is not None:
            try:
                if float(overspend) > 0:
                    overspend_class = "text-danger"
            except Exception:
                # If somehow not numeric, leave neutral
                overspend_class = ""

        rows_html.append(
            f"""
            <tr>
              <td>
                <a class="it-linked-panel__link" href="{escape_html(url)}" target="_blank" rel="noopener">
                  {escape_html(b.name)}
                </a>
              </td>
              <td class="it-linked-panel__mono">{escape_html(str(b.total) if b.total is not None else "")}</td>
              <td class="it-linked-panel__mono {overspend_class}">{escape_html(str(overspend) if overspend is not None else "")}</td>
            </tr>
            """
        )

    return f"""
    <div class="it-linked-panel">
      <div class="it-linked-panel__header">
        <div class="it-linked-panel__title">Linked Bills (MSISDN: {escape_html(doc.msisdn)})</div>
        <div class="it-linked-panel__count">{len(bills)}</div>
      </div>

      <div class="it-linked-panel__table-wrap">
        <table class="table table-bordered table-hover">
          <thead>
            <tr>
              <th>Monthly Bill</th>
              <th>Total</th>
              <th>Overspend</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </div>
    """
