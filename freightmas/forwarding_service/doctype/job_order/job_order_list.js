// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
// List View Settings for Job Order

frappe.listview_settings["Job Order"] = {
	add_fields: ["order_date", "customer", "quotation_reference", "forwarding_job_reference", "docstatus"],
	
	get_indicator: function(doc) {
		if (doc.docstatus === 0) {
			return [__("Draft"), "gray", "docstatus,=,0"];
		} else if (doc.docstatus === 1) {
			if (doc.forwarding_job_reference) {
				return [__("Converted"), "green", "forwarding_job_reference,!=,''"];
			} else {
				return [__("Submitted"), "blue", "docstatus,=,1"];
			}
		} else if (doc.docstatus === 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		}
	},
	
	onload: function(listview) {
		// Add custom filter for unconverted orders
		listview.page.add_inner_button(__("Pending Conversion"), function() {
			listview.filter_area.clear();
			listview.filter_area.add([[listview.doctype, "docstatus", "=", 1]]);
			listview.filter_area.add([[listview.doctype, "forwarding_job_reference", "is", "not set"]]);
		});
	}
};
