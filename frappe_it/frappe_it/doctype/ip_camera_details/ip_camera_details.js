// Copyright (c) 2025, BuFf0k and contributors
// For license information, please see license.txt

// IP address validation and the Camera Link are set server-side on save.
frappe.ui.form.on('IP Camera Details', {
    refresh: function (frm) {
        frappe.require('/assets/frappe_it/js/device_password.js', () => frappe_it.device_password.setup(frm));
    }
});
