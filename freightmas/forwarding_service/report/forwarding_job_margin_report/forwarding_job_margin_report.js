// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Forwarding Job Margin Report"] = {
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
				const date_range = frappe.query_report.get_filter_value("date_range");
				const today = frappe.datetime.get_today();
				let from_date, to_date;

				switch (date_range) {
					case "Today":
						from_date = to_date = today; break;
					case "Yesterday":
						from_date = to_date = frappe.datetime.add_days(today, -1); break;
					case "This Week":
						from_date = frappe.datetime.week_start();
						to_date   = frappe.datetime.week_end(); break;
					case "Last Week":
						from_date = frappe.datetime.add_days(frappe.datetime.week_start(), -7);
						to_date   = frappe.datetime.add_days(frappe.datetime.week_end(), -7); break;
					case "This Month":
						from_date = frappe.datetime.month_start();
						to_date   = frappe.datetime.month_end(); break;
					case "Last Month":
						from_date = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
						to_date   = frappe.datetime.add_days(frappe.datetime.month_start(), -1); break;
					case "This Year":
						from_date = frappe.datetime.year_start();
						to_date   = frappe.datetime.year_end(); break;
					case "Last Year":
						const last_year = parseInt(today.split("-")[0]) - 1;
						from_date = `${last_year}-01-01`;
						to_date   = `${last_year}-12-31`; break;
					default:
						return;
				}

				if (date_range && date_range !== "Custom" && date_range !== "") {
					frappe.query_report.set_filter_value("from_date", from_date);
					frappe.query_report.set_filter_value("to_date", to_date);
				}
			}
		},
		{
			fieldname: "date_field",
			label: __("Date Field"),
			fieldtype: "Select",
			options: "\nCreation Date\nRevenue Recognition Date",
			default: "Creation Date"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			only_select: true
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			only_select: true
		},
		{
			fieldname: "shipment_mode",
			label: __("Shipment Mode"),
			fieldtype: "Select",
			options: "\nSea\nAir\nRoad"
		},
		{
			fieldname: "direction",
			label: __("Direction"),
			fieldtype: "Select",
			options: "\nImport\nExport\nLocal\nTransit"
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nIn Progress\nDelivered\nCompleted\nClosed"
		}
	],

	onload: function(report) {
		report.page.add_inner_button(__("Export to Excel"), function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_excel?report_name=Forwarding Job Margin Report&filters=${query}`;
			window.open(url);
		}, __("Export"));

		report.page.add_inner_button(__("Export to PDF"), function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=Forwarding Job Margin Report&filters=${query}`;
			window.open(url);
		}, __("Export"));

		report.page.add_button(__("Clear Filters"), function() {
			report.filters.forEach(filter => {
				report.set_filter_value(filter.df.fieldname, filter.df.default || "");
			});
			report.refresh();
		});
	}
};
