// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Reconciliation History per Cash Account"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1 },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "cash_account", label: __("Cash Account"), fieldtype: "Link", options: "Account", get_query: cash_reconciliation_account_query },
		{ fieldname: "branch", label: __("Branch / Station"), fieldtype: "Data" },
		{ fieldname: "cashier", label: __("Cashier"), fieldtype: "Link", options: "User" },
		{ fieldname: "reconciliation_status", label: __("Status"), fieldtype: "Select", options: "\nBalanced\nDifference" },
	],
};

function cash_reconciliation_account_query() {
	return { filters: { company: frappe.query_report.get_filter_value("company"), account_type: "Cash", is_group: 0 } };
}
