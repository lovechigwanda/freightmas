// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Quotation List"] = {
	"filters": [
		{
			fieldname: "date_range",
			label: __("Date Range"),
			fieldtype: "Select",
			options: [
				"",
				"Today",
				"Yesterday",
				"This Week",
				"Last Week",
				"This Month",
				"Last Month",
				"This Year",
				"Last Year",
				"Custom"
			],
			default: "This Month",
			on_change: function() {
				let date_range = frappe.query_report.get_filter_value('date_range');
				let today = frappe.datetime.get_today();
				let from_date, to_date;

				switch(date_range) {
					case "Today":
						from_date = to_date = today;
						break;
					case "Yesterday":
						from_date = to_date = frappe.datetime.add_days(today, -1);
						break;
					case "This Week":
						from_date = frappe.datetime.week_start(today);
						to_date = frappe.datetime.week_end(today);
						break;
					case "Last Week":
						let last_week_start = frappe.datetime.add_days(frappe.datetime.week_start(today), -7);
						from_date = last_week_start;
						to_date = frappe.datetime.add_days(last_week_start, 6);
						break;
					case "This Month":
						from_date = frappe.datetime.month_start(today);
						to_date = frappe.datetime.month_end(today);
						break;
					case "Last Month":
						let last_month = frappe.datetime.add_months(today, -1);
						from_date = frappe.datetime.month_start(last_month);
						to_date = frappe.datetime.month_end(last_month);
						break;
					case "This Year":
						let current_year = frappe.datetime.year_start(today);
						from_date = current_year;
						to_date = frappe.datetime.year_end(today);
						break;
					case "Last Year":
						let last_year = new Date(today.split('-')[0] - 1, 0, 1).getFullYear();
						from_date = `${last_year}-01-01`;
						to_date = `${last_year}-12-31`;
						break;
					default:
						from_date = frappe.query_report.get_filter_value('from_date');
						to_date = frappe.query_report.get_filter_value('to_date');
				}

				if (date_range && date_range !== "Custom" && date_range !== "") {
					frappe.query_report.set_filter_value('from_date', from_date);
					frappe.query_report.set_filter_value('to_date', to_date);
				}
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			only_select: true
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Draft", "Pending Approval", "Approved", "Sent to Customer", "Accepted", "Rejected", "Expired", "Cancelled"]
		},
		{
			fieldname: "customer_reference",
			label: __("Reference"),
			fieldtype: "Data"
		}
	],

	onload: function(report) {
		// Add New Quotation button
		report.page.set_primary_action(__('Add Quotation'), function() {
			frappe.new_doc('Quotation');
		});

		// Add Export buttons
		report.page.add_inner_button('Export to Excel', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_excel?report_name=Quotation List&filters=${query}`;
			window.open(url);
		}, 'Export');

		report.page.add_inner_button('Export to PDF', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=Quotation List&filters=${query}`;
			window.open(url);
		}, 'Export');

		report.page.add_inner_button('Clear Filters', function() {
			// Clear each filter to its default value
			report.filters.forEach(filter => {
				let default_value = filter.df.default || "";
				report.set_filter_value(filter.df.fieldname, default_value);
			});
			
			// Trigger report refresh after clearing filters
			report.refresh();
		});
	}
};
