// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Milestone Definition", {
	setup(frm) {
		// Stage must belong to the same service module as the milestone.
		frm.set_query("stage", function () {
			return {
				filters: {
					service_module: frm.doc.service_module || "",
					is_active: 1,
				},
			};
		});
	},

	service_module(frm) {
		// Clear a stale stage when the module changes so it can't point at
		// another module's stage.
		if (frm.doc.stage) {
			frm.set_value("stage", null);
		}
	},
});
