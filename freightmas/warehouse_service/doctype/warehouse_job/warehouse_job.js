// Copyright (c) 2025, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job', {
	refresh: function(frm) {
		// Add custom buttons for workflow actions
		if (frm.doc.docstatus === 1 && frm.doc.status === "Active") {
			frm.add_custom_button(__('Mark as Completed'), function() {
				frappe.call({
					method: 'frappe.client.set_value',
					args: {
						doctype: 'Warehouse Job',
						name: frm.doc.name,
						fieldname: 'status',
						value: 'Completed'
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			});
		}
	},
	
	fiscal_year: function(frm) {
		// Auto-populate job dates from fiscal year
		if (frm.doc.fiscal_year && frm.is_new()) {
			frappe.db.get_value('Fiscal Year', frm.doc.fiscal_year, ['year_start_date', 'year_end_date'], (r) => {
				if (r) {
					// Set job start date to today or fiscal year start (whichever is later)
					let today = frappe.datetime.get_today();
					let fy_start = r.year_start_date;
					frm.set_value('job_start_date', frappe.datetime.str_to_obj(today) > frappe.datetime.str_to_obj(fy_start) ? today : fy_start);
					
					// Set job end date to fiscal year end
					frm.set_value('job_end_date', r.year_end_date);
				}
			});
		}
	},
	
	job_start_date: function(frm) {
		frm.trigger('calculate_validity');
	},
	
	job_end_date: function(frm) {
		frm.trigger('calculate_validity');
	},
	
	calculate_validity: function(frm) {
		if (frm.doc.job_start_date && frm.doc.job_end_date) {
			let days = frappe.datetime.get_day_diff(frm.doc.job_end_date, frm.doc.job_start_date) + 1;
			frm.set_value('job_validity_days', days);
		}
	}
});
