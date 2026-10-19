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
