// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Account Ledger vs Reconciled Balance"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1 },
		{ fieldname: "as_of_date", label: __("As of Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "from_date", label: __("Reconciled From"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("Reconciled To"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "cash_account", label: __("Cash Account"), fieldtype: "Link", options: "Account", get_query: cash_reconciliation_account_query },
		{ fieldname: "branch", label: __("Branch / Station"), fieldtype: "Data" },
		{ fieldname: "cashier", label: __("Cashier"), fieldtype: "Link", options: "User" },
	],
};

function cash_reconciliation_account_query() {
	return { filters: { company: frappe.query_report.get_filter_value("company"), account_type: "Cash", is_group: 0 } };
}
