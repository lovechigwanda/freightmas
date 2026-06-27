// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Invoice Register Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 0,
			"width": "120px"
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 0,
			"width": "120px"
		},
		{
			"fieldname": "party",
			"label": "Party",
			"fieldtype": "Data",
			"reqd": 0,
			"width": "150px"
		},
		{
			"fieldname": "bl_number",
			"label": "BL Number",
			"fieldtype": "Data",
			"reqd": 0,
			"width": "150px"
		}
	]
};
