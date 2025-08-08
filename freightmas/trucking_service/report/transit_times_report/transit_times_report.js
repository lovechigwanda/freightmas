// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Transit Times Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "route",
			"label": __("Route"),
			"fieldtype": "Link",
			"options": "Route"
		},
		{
			"fieldname": "show_variance_only",
			"label": __("Show Trips with Variance Only"),
			"fieldtype": "Check"
		}
	]
};
