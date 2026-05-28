frappe.ui.form.on("Sales Invoice", {
	setup(frm) {
		frm.ignore_doctypes_on_cancel_all = [
			"Trip",
			"Forwarding Job",
			"Clearing Job",
			"Road Freight Job",
			"Border Clearing Job",
			"Warehouse Job",
			"Trip Bulk Sales Invoice",
		];
	},
	refresh(frm) {
		set_forwarding_job_query(frm);
	},
	is_forwarding_invoice(frm) {
		set_forwarding_job_query(frm);
	},
	link_closed_forwarding_job(frm) {
		frm.set_value("forwarding_job_reference", null);
		set_forwarding_job_query(frm);
	},
});

function set_forwarding_job_query(frm) {
	frm.set_query("forwarding_job_reference", function () {
		if (frm.doc.link_closed_forwarding_job) {
			return {
				filters: [["Forwarding Job", "docstatus", "in", [0, 1]]],
			};
		}
		return {
			filters: [["Forwarding Job", "docstatus", "=", 0]],
		};
	});
}
