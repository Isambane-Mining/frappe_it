// Copyright (c) 2026, buff0k and contributors
// For license information, please see license.txt

// "Show Password" button for IP Camera Details / NVR Details. The password
// is fetched on demand (each reveal is logged on the record) and never kept
// on the form.
frappe.provide('frappe_it.device_password');

frappe_it.device_password.setup = function (frm) {
    if (frm.is_new()) return;
    if (!frappe.user.has_role(['IT Manager', 'IT User', 'System Manager'])) return;

    frm.add_custom_button(__('Show Password'), () => {
        frappe.call({
            method: 'frappe_it.controllers.device_credentials.reveal_device_password',
            type: 'POST',
            args: { doctype: frm.doctype, name: frm.doc.name },
        }).then((r) => {
            if (!r.message) {
                frappe.msgprint(__('No password is stored for this device.'));
                return;
            }

            const dialog = new frappe.ui.Dialog({
                title: __('Password for {0}', [frm.doc.name]),
                fields: [
                    { fieldtype: 'Data', fieldname: 'username', label: __('Username'), read_only: 1, default: frm.doc.username },
                    { fieldtype: 'Data', fieldname: 'password', label: __('Password'), read_only: 1, default: r.message },
                ],
                primary_action_label: __('Copy Password'),
                primary_action() {
                    frappe.utils.copy_to_clipboard(r.message);
                    dialog.hide();
                },
            });
            dialog.onhide = () => frm.reload_doc();  // show the new audit comment
            dialog.show();
        });
    });
};
