// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse Inventory Summary"] = {
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
			fieldname: "uom",
			label: __("UOM"),
			fieldtype: "Link",
			options: "UOM"
		},
		{
			fieldname: "warehouse_bay",
			label: __("Warehouse Bay"),
			fieldtype: "Link",
			options: "Warehouse Bay"
		}
	]
};
