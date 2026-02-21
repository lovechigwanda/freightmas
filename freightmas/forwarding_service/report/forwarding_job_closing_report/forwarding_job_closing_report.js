// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Forwarding Job Closing Report"] = {
	"filters": [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nCompleted\nClosed",
			default: ""
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		}
	],

	onload: function(report) {
		// Standard Excel Export
		report.page.add_inner_button('Export to Excel', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_excel?report_name=Forwarding Job Closing Report&filters=${query}`;
			window.open(url);
		}, 'Export');

		// Clear Filters
		report.page.add_inner_button('Clear Filters', function() {
			report.filters.forEach(filter => {
				let default_value = filter.df.default || "";
				report.set_filter_value(filter.df.fieldname, default_value);
			});
			report.refresh();
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Color-code status
		if (column.fieldname === "status" && data) {
			let color = "gray";
			if (data.status === "Completed") color = "orange";
			else if (data.status === "Closed") color = "green";

			value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		}

		// Color-code revenue recognised
		if (column.fieldname === "revenue_recognised" && data) {
			let color = data.revenue_recognised === "Yes" ? "green" : "red";
			value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		}

		return value;
	}
};
