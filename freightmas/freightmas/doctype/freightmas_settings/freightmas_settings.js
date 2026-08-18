// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("FreightMas Settings", {
	refresh(frm) {
		if (frm.doc.enable_shipping_tracker && frm.doc.tracking_provider === "Traqo") {
			frappe.call({
				method: "freightmas.freightmas.doctype.freightmas_settings.freightmas_settings.get_traqo_webhook_url_api",
				callback(r) {
					if (r.message) {
						frm.set_value("traqo_webhook_url", r.message);
					}
				},
			});
		}
	},
});
