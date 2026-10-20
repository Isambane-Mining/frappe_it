// Copyright (c) 2025, buff0k and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Allocation', {
    setup: function (frm) {
        // Only submitted, in-service Assets can be allocated (enforced on save too)
        frm.set_query('asset', 'list_of_allocated_assets', function () {
            return {
                filters: {
                    docstatus: 1,
                    status: ['not in', ['Scrapped', 'Sold']],
                },
            };
        });
    },

    employee_or_asset: function (frm) {
        const selected_doctype = frm.doc.employee_or_asset;

        if (!selected_doctype) {
            frm.set_value('branch_or_location', null);
            frm.set_value('site', null);
            frm.set_value('employee_asset_name', null);
            return;
        }

        // Set branch_or_location based on the selected doctype
        if (selected_doctype === 'Employee') {
            frm.set_value('branch_or_location', 'Branch');
        } else if (['Asset', 'Location'].includes(selected_doctype)) {
            frm.set_value('branch_or_location', 'Location');
        }

        // Clear dependent fields until new data is fetched
        frm.set_value('site', null);
        frm.set_value('employee_asset_name', null);

        frm.trigger('update_site_and_name');
    },

    allocated_to: function (frm) {
        frm.trigger('update_site_and_name');
    },

    update_site_and_name: function (frm) {
        const selected_doctype = frm.doc.employee_or_asset;
        const docname = frm.doc.allocated_to;

        if (!selected_doctype || !docname) {
            frm.set_value('site', null);
            frm.set_value('employee_asset_name', null);
            return;
        }

        frappe.call({
            method: 'frappe_it.controllers.lookups.get_holder_details',
            args: {
                doctype: selected_doctype,
                docname: docname,
            },
            callback: function (r) {
                const details = r.message || {};
                frm.set_value('site', details.site || null);
                frm.set_value('employee_asset_name', details.name || null);
            }
        });
    }
});

frappe.ui.form.on('Asset Allocation Table', {
    asset: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.asset) {
            frappe.model.set_value(cdt, cdn, 'asset_name', '');
            return;
        }

        frappe.call({
            method: 'frappe_it.frappe_it.doctype.asset_allocation.asset_allocation.check_asset_allocation',
            args: {
                asset: row.asset,
                docname: frm.doc.name
            },
            callback: function (r) {
                if (r.message && r.message.length > 0) {
                    frappe.msgprint({
                        title: __('Asset Already Allocated'),
                        message: __('The asset {0} is already allocated in: {1}', [row.asset, r.message.join(', ')]),
                        indicator: 'red'
                    });
                    frappe.model.set_value(cdt, cdn, 'asset', '');
                    return;
                }

                frappe.db.get_value('Asset', row.asset, ['item_name', 'asset_name']).then(({ message }) => {
                    if (message) {
                        frappe.model.set_value(cdt, cdn, 'asset_name', `${message.item_name || ''} - ${message.asset_name || ''}`);
                    }
                });
            }
        });
    }
});
