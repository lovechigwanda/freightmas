// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Trip Bulk Sales Invoice', {
    onload: function(frm) {
        if (!frm.doc.company) {
            frappe.call({
                method: "frappe.defaults.get_defaults",
                callback: function(r) {
                    if (r.message && r.message.company) {
                        frm.set_value("company", r.message.company);
                    }
                }
            });
        }
    }
});
