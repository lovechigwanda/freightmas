// Copyright (c) 2026, Codes Soft and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse Item Balance Summary"] = {
	"filters": [
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "item_name",
			"label": __("Item Name"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "show_zero_balance",
			"label": __("Show Zero Balance Items"),
			"fieldtype": "Check",
			"default": 0
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight rows with zero balance
		if (column.fieldname == "total_quantity" && data && data.total_quantity == 0) {
			value = "<span style='color: #999;'>" + value + "</span>";
		}
		
		return value;
	}
};
