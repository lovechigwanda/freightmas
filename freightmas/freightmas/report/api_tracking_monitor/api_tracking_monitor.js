// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["API Tracking Monitor"] = {
	filters: [
		{
			fieldname: "date_range",
			label: __("Date Range"),
			fieldtype: "Select",
			options: [
				"",
				"Today",
				"This Week",
				"This Month",
				"Last Month",
				"This Year",
				"Custom"
			],
			default: "",
			on_change: function () {
				apply_date_range_filter();
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "tracking_status",
			label: __("Tracking Status"),
			fieldtype: "Select",
			options: [
				"",
				"IN_TRANSIT",
				"DELIVERED",
				"ARRIVED",
				"Never Fetched"
			]
		}
	]
};

function apply_date_range_filter() {
	let date_range = frappe.query_report.get_filter_value("date_range");
	let today = frappe.datetime.get_today();
	let from_date, to_date;

	switch (date_range) {
		case "Today":
			from_date = to_date = today;
			break;
		case "This Week":
			from_date = frappe.datetime.week_start();
			to_date = frappe.datetime.week_end();
			break;
		case "This Month":
			from_date = frappe.datetime.month_start();
			to_date = frappe.datetime.month_end();
			break;
		case "Last Month":
			from_date = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
			to_date = frappe.datetime.add_days(frappe.datetime.month_start(), -1);
			break;
		case "This Year":
			from_date = frappe.datetime.year_start();
			to_date = frappe.datetime.year_end();
			break;
		default:
			return;
	}

	if (date_range && date_range !== "Custom" && date_range !== "") {
		frappe.query_report.set_filter_value("from_date", from_date);
		frappe.query_report.set_filter_value("to_date", to_date);
	}
}
