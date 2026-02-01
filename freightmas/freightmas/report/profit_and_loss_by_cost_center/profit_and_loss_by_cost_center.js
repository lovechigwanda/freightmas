// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
// For license information, please see license.txt

frappe.query_reports["Profit and Loss by Cost Center"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year", "Date Range"],
			default: "Fiscal Year",
			reqd: 1,
			on_change: function () {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
				frappe.query_report.toggle_filter_display(
					"from_fiscal_year",
					filter_based_on !== "Fiscal Year"
				);
				frappe.query_report.toggle_filter_display(
					"to_fiscal_year",
					filter_based_on !== "Fiscal Year"
				);
				frappe.query_report.toggle_filter_display(
					"from_date",
					filter_based_on !== "Date Range"
				);
				frappe.query_report.toggle_filter_display(
					"to_date",
					filter_based_on !== "Date Range"
				);

				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
			on_change: function () {
				set_dates_from_fiscal_year();
			},
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
			on_change: function () {
				set_dates_from_fiscal_year();
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			options: "Cost Center",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
					is_group: 0,
				});
			},
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Link",
			options: "Currency",
			get_query: function () {
				return {
					filters: {
						enabled: 1,
					},
				};
			},
		},
		{
			fieldname: "include_closing_entries",
			label: __("Include Closing Entries"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "include_default_book_entries",
			label: __("Include Default FB Entries"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_zero_values",
			label: __("Show Zero Values"),
			fieldtype: "Check",
			default: 0,
		},
	],

	onload: function (report) {
		// Set initial filter visibility
		setTimeout(function () {
			let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
			frappe.query_report.toggle_filter_display(
				"from_fiscal_year",
				filter_based_on !== "Fiscal Year"
			);
			frappe.query_report.toggle_filter_display(
				"to_fiscal_year",
				filter_based_on !== "Fiscal Year"
			);
			frappe.query_report.toggle_filter_display(
				"from_date",
				filter_based_on !== "Date Range"
			);
			frappe.query_report.toggle_filter_display(
				"to_date",
				filter_based_on !== "Date Range"
			);

			// Set dates from fiscal year on load
			set_dates_from_fiscal_year();
		}, 500);
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Bold the total row and root level accounts
		if (data && !data.parent_account) {
			value = "<b>" + value + "</b>";
		}

		// Color negative values red
		if (column.fieldtype === "Currency" && data && data[column.fieldname] < 0) {
			value = "<span style='color: red;'>" + value + "</span>";
		}

		return value;
	},

	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
};

function set_dates_from_fiscal_year() {
	let from_fiscal_year = frappe.query_report.get_filter_value("from_fiscal_year");
	let to_fiscal_year = frappe.query_report.get_filter_value("to_fiscal_year");

	if (from_fiscal_year && to_fiscal_year) {
		frappe.call({
			method: "freightmas.freightmas.report.profit_and_loss_by_cost_center.profit_and_loss_by_cost_center.get_fiscal_year_data",
			args: {
				from_fiscal_year: from_fiscal_year,
				to_fiscal_year: to_fiscal_year,
			},
			callback: function (r) {
				if (r.message) {
					frappe.query_report.set_filter_value({
						from_date: r.message.from_date,
						to_date: r.message.to_date,
					});
				}
			},
		});
	}
}
