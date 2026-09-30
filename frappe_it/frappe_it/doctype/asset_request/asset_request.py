# Copyright (c) 2025, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

# Asset types with a structured specification DocType. Every other asset type
# is specified free-form in manual_spec. Keep in sync with asset_request.js.
SPEC_DOCTYPE_BY_ASSET_TYPE = {
    "Cellular Telephone": "Cellphone Plan by Designation",
    "Cellphone Simcards": "Cellphone Plan by Designation",
    "Laptop Computer": "Laptop Specification",
}


class AssetRequest(Document):
    def validate(self):
        self.validate_asset_request_list()

    def validate_asset_request_list(self):
        for row in self.asset_request_list:
            row.doctype_link = SPEC_DOCTYPE_BY_ASSET_TYPE.get(row.asset_type)

            if row.doctype_link:
                row.manual_spec = None
                continue

            row.asset_spec = None
            row.asset_spec_details = None
            if not (row.manual_spec or "").strip():
                frappe.throw(
                    _("Row #{0}: Please enter the specifications for {1}.").format(
                        row.idx, row.asset_type
                    ),
                    title=_("Specifications Required"),
                )

    def before_submit(self):
        if not self.attach_signed:
            frappe.throw(_("Please attach a signed copy before submitting."))

@frappe.whitelist()
def get_employee_or_asset_details(doctype, docname):
    if not doctype or not docname:
        frappe.throw(_("Invalid parameters provided."))

    try:
        if doctype == "Employee":
            # Fetch linked Branch and Employee Name
            doc = frappe.get_doc("Employee", docname)
            return {
                "allocate_to_site": doc.branch if doc.branch else _("Branch not found"),
                "employee_asset_name": doc.employee_name if doc.employee_name else _("Name not found"),
                "employee_asset_designation": doc.designation if doc.designation else _("Designation not found"),
            }
        elif doctype == "Asset":
            # Fetch linked Location and Item Name
            doc = frappe.get_doc("Asset", docname)
            return {
                "allocate_to_site": doc.location if doc.location else _("Location not found"),
                "employee_asset_name": doc.item_name if doc.item_name else _("Name not found"),
            }
        elif doctype == "Location":
            # Fetch linked Location and Item Name
            doc = frappe.get_doc("Location", docname)
            return {
                "allocate_to_site": doc.name if doc.name else _("Location not found"),
                "employee_asset_name": doc.name if doc.name else _("Location not found"),
            }
        else:
            frappe.throw(_("Invalid Doctype: {0}").format(doctype))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in get_employee_or_asset_details"))
        frappe.throw(_("An error occurred while fetching the document data: {0}").format(str(e)))