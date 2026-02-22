frappe.ui.form.on("Sales Invoice", {
	setup(frm) {
		frm.ignore_doctypes_on_cancel_all = [
			"Trip",
			"Forwarding Job",
			"Clearing Job",
			"Road Freight Job",
			"Warehouse Job",
			"Trip Bulk Sales Invoice",
		];
	},
});
