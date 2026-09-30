// Copyright (c) 2025, buff0k and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Request', {
    onload: function (frm) {
        // Default requested_by to logged-in user's Employee record on create
        if (frm.is_new()) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: { user_id: frappe.session.user },
                    fields: ['name']
                },
                callback: function (r) {
                    if (r.message && r.message.length) {
                        frm.set_value('requested_by', r.message[0].name);
                    }
                }
            });
        }
    },

    company: function(frm) {
        if (frm.doc.company) {
            frappe.db.get_doc('Company', frm.doc.company).then(company => {
                if (company.default_letter_head) {
                    frm.set_value('letter_head', company.default_letter_head);
                } else {
                    frm.set_value('letter_head', '');
                    frappe.msgprint('This company has no default Letter Head set.');
                }
            });
        }
    },

    requested_by: function (frm) {
        if (frm.doc.requested_by) {
            frappe.db.get_doc('Employee', frm.doc.requested_by)
                .then(employee => {
                    frm.set_value('requested_by_site', employee.branch || '');
                    frm.set_value('requested_by_designation', employee.designation || '');
                    frm.set_value('requested_by_names', employee.employee_name || '');
                })
                .catch(err => {
                    frappe.msgprint(__('Failed to fetch employee details'));
                    console.error(err);
                });
        }
    },

    employee_or_asset: function (frm) {
        const selected_doctype = frm.doc.employee_or_asset;

        if (!selected_doctype) {
            frm.set_value('branch_or_location', null);
            frm.set_value('allocate_to_site', null);
            frm.set_value('employee_asset_name', null);
            return;
        }

        if (selected_doctype === 'Employee') {
            frm.set_value('branch_or_location', 'Branch');
        } else if (['Asset', 'Location'].includes(selected_doctype)) {
            frm.set_value('branch_or_location', 'Location');
        }

        frm.set_value('allocate_to_site', null);
        frm.set_value('employee_asset_name', null);

        frm.trigger('update_site_and_name');
    },

    allocate_to: function (frm) {
        frm.trigger('update_site_and_name');
    },

    update_site_and_name: function (frm) {
        const selected_doctype = frm.doc.employee_or_asset;
        const docname = frm.doc.allocate_to;

        if (!selected_doctype || !docname) {
            frm.set_value('allocate_to_site', null);
            frm.set_value('employee_asset_name', null);
            frm.set_value('employee_asset_designation', null);
            return;
        }

        frappe.call({
            method: 'frappe_it.frappe_it.doctype.asset_request.asset_request.get_employee_or_asset_details',
            args: {
                doctype: selected_doctype,
                docname: docname,
            },
            callback: function (response) {
                if (response.message) {
                    const { allocate_to_site, employee_asset_name, employee_asset_designation } = response.message;
                    frm.set_value('allocate_to_site', allocate_to_site || null);
                    frm.set_value('employee_asset_name', employee_asset_name || null);
                    frm.set_value('employee_asset_designation', employee_asset_designation || null);
                } else {
                    frm.set_value('allocate_to_site', null);
                    frm.set_value('employee_asset_name', null);
                    frm.set_value('employee_asset_designation', null);
                }
            }
        });
    }
});

// Asset types with a structured specification DocType. Every other asset type
// is specified free-form in manual_spec. Keep in sync with asset_request.py.
frappe.provide('frappe_it.asset_request');
frappe_it.asset_request.SPEC_DOCTYPE_BY_ASSET_TYPE = {
    'Cellular Telephone': 'Cellphone Plan by Designation',
    'Cellphone Simcards': 'Cellphone Plan by Designation',
    'Laptop Computer': 'Laptop Specification',
};

frappe.ui.form.on('Asset Request List', {
    asset_type: async function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const spec_doctype = frappe_it.asset_request.SPEC_DOCTYPE_BY_ASSET_TYPE[row.asset_type] || null;

        // Reset whatever was captured for the previously selected asset type;
        // doctype_link drives which spec fields are shown (depends_on).
        await frappe.model.set_value(cdt, cdn, {
            doctype_link: spec_doctype,
            asset_spec: null,
            asset_spec_details: null,
            manual_spec: null,
        });

        const designation = frm.doc.employee_asset_designation;
        if (!spec_doctype || !designation) return;

        // Preselect the spec assigned to the allocatee's designation
        const matches = await frappe.db.get_list(spec_doctype, {
            filters: [['Cellphone Plan Designation List', 'designation', '=', designation]],
            fields: ['name'],
            limit: 1,
        });

        // Setting asset_spec fires the asset_spec handler, which fills asset_spec_details
        if (matches.length) {
            await frappe.model.set_value(cdt, cdn, 'asset_spec', matches[0].name);
        }
    },

    asset_spec: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.doctype_link || !row.asset_spec) {
            frappe.model.set_value(cdt, cdn, "asset_spec_details", null);
            return;
        }

        frappe.db.get_doc(row.doctype_link, row.asset_spec).then(spec => {
            if (row.doctype_link === "Laptop Specification") {
                let detail = [
                    spec.cpu || "",
                    spec.ram || "",
                    spec.storage || "",
                    spec.gpu || ""
                ].filter(Boolean).join(', ');
                frappe.model.set_value(cdt, cdn, "asset_spec_details", detail);
            }

            else if (row.doctype_link === "Cellphone Plan by Designation") {
                if (!spec.cellphone_plan) return;

                frappe.db.get_doc("Cellphone Plan", spec.cellphone_plan).then(plan => {
                    let detail = [
                        plan.bundled_minutes || "",
                        plan.bundled_data || ""
                    ].filter(Boolean).join(', ');
                    frappe.model.set_value(cdt, cdn, "asset_spec_details", detail);
                });
            }
        });
    }
});
