// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Truck Register"] = {
	"filters": [
		{
			fieldname: "truck_status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nAvailable\nNot Available"
		},
		{
			fieldname: "driver_linked",
			label: __("Driver Linked"),
			fieldtype: "Select",
			options: "\nYes\nNo"
		}
	],

	onload: function(report) {
		report.page.add_inner_button('Export to Excel', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_excel?report_name=Truck Register&filters=${query}`;
			window.open(url);
		}, 'Export');

		report.page.add_inner_button('Export to PDF', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=Truck Register&filters=${query}`;
			window.open(url);
		}, 'Export');

		// Add Clear Filters button
		report.page.add_inner_button('Clear Filters', function() {
			report.filters.forEach(filter => {
				let default_value = filter.df.default || "";
				report.set_filter_value(filter.df.fieldname, default_value);
			});
		});
	}
};
