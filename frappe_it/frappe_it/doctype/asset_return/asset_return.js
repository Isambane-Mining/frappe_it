// Copyright (c) 2025, buff0k and contributors
// For license information, please see license.txt

function get_employee_details(employee) {
    return frappe.call({
        method: 'frappe_it.controllers.lookups.get_holder_details',
        args: { doctype: 'Employee', docname: employee },
    }).then(r => r.message || {});
}

frappe.ui.form.on("Asset Return", {
    receiver: async function (frm) {
        if (!frm.doc.receiver) return;

        const employee = await get_employee_details(frm.doc.receiver);
        frm.set_value('receiver_branch', employee.site || '');
        frm.set_value('receiver_designation', employee.designation || '');
        frm.set_value('receiver_name', employee.name || '');
    },

    employee: async function (frm) {
        if (!frm.doc.employee) return;

        const employee = await get_employee_details(frm.doc.employee);
        frm.set_value('branch', employee.site || '');
        frm.set_value('designation', employee.designation || '');
        frm.set_value('employee_name', employee.name || '');

        // Pre-fill with what is currently allocated to this employee
        const allocations = await frappe.db.get_list('Asset Allocation', {
            fields: ['name'],
            filters: {
                employee_or_asset: 'Employee',
                allocated_to: frm.doc.employee
            }
        });

        frm.clear_table('list_of_allocated_assets');

        for (let alloc of allocations) {
            const alloc_doc = await frappe.db.get_doc('Asset Allocation', alloc.name);
            for (let asset_row of alloc_doc.list_of_allocated_assets || []) {
                let new_row = frm.add_child('list_of_allocated_assets');
                new_row.asset = asset_row.asset;
                new_row.asset_name = asset_row.asset_name;
                new_row.check_in_date = frappe.datetime.get_today();
                new_row.condition_photo_out = asset_row.condition_photo;
                new_row.notes = asset_row.notes;
            }
        }

        frm.refresh_field('list_of_allocated_assets');
    }
});

frappe.ui.form.on('Asset Return Table', {
    asset: function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.asset) return;

        frappe.db.get_value('Asset', row.asset, 'asset_name')
            .then(r => {
                if (r.message && r.message.asset_name) {
                    frappe.model.set_value(cdt, cdn, 'asset_name', r.message.asset_name);
                }
            });
    }
});
