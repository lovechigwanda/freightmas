// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Unbilled Revenue Aging"] = {
	"filters": [
		{ fieldname: "as_of_date", label: __("As Of Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "service", label: __("Service"), fieldtype: "Select", options: "\nForwarding\nClearing\nTrucking\nRoad Freight" },
	]
};
