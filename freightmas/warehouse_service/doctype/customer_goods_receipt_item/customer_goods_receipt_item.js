// Copyright (c) 2025, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Goods Receipt Item', {
	warehouse_bay: function(frm, cdt, cdn) {
		// Clear warehouse bin when bay changes
		let row = locals[cdt][cdn];
		if (row.warehouse_bin) {
			frappe.model.set_value(cdt, cdn, 'warehouse_bin', '');
		}
	}
});
