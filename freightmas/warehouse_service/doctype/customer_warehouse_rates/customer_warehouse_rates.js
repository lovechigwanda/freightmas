// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Warehouse Rates', {
	refresh: function(frm) {
		// Add custom behavior if needed
	},
	
	storage_rate_per_day: function(frm) {
		// Auto-calculate monthly rate (30 days)
		// Apply precision rounding (2 decimal places for currency fields)
		if (frm.doc.storage_rate_per_day && !frm.doc.storage_rate_per_month) {
			frm.set_value('storage_rate_per_month', flt(frm.doc.storage_rate_per_day * 30, 2));
		}
	},

	storage_rate_per_month: function(frm) {
		// Auto-calculate daily rate
		// Apply precision rounding (2 decimal places for currency fields)
		if (frm.doc.storage_rate_per_month && !frm.doc.storage_rate_per_day) {
			frm.set_value('storage_rate_per_day', flt(frm.doc.storage_rate_per_month / 30, 2));
		}
	}
});
