// Copyright (c) 2026, BuFf0k
// For license information, please see license.txt

frappe.ui.form.on("NVR Details", {
    refresh: function(frm) {
        render_linked_cameras_html(frm);
        frappe.require('/assets/frappe_it/js/device_password.js', () => frappe_it.device_password.setup(frm));
    },

    after_save: function(frm) {
        render_linked_cameras_html(frm);
    }
});


function render_linked_cameras_html(frm) {
    if (!frm.fields_dict.linked_cameras_html) return;

    frappe.require('/assets/frappe_it/css/it_ui.css');

    if (frm.is_new() || frm.doc.__islocal) {
        frm.fields_dict.linked_cameras_html.$wrapper.html(`
            <div class="it-linked-panel">
              <div class="it-linked-panel__empty">
                Linked cameras will appear here once the record is saved.
              </div>
            </div>
        `);
        return;
    }

    frappe.call({
        method: 'frappe_it.frappe_it.doctype.nvr_details.nvr_details.get_linked_cameras_html',
        args: { nvr_details_name: frm.doc.name },
        callback: function(r) {
            frm.fields_dict.linked_cameras_html.$wrapper.html(r.message || '');
        }
    });
}
