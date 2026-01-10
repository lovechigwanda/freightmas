// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse Unbilled Charges"] = {
	"filters": [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "warehouse_job",
			label: __("Warehouse Job"),
			fieldtype: "Link",
			options: "Warehouse Job"
		},
		{
			fieldname: "charge_type",
			label: __("Charge Type"),
			fieldtype: "Select",
			options: [
				"",
				"Handling",
				"Storage",
				"Both"
			],
			default: "Both"
		}
	]
};
