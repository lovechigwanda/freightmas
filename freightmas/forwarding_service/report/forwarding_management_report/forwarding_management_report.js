// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Forwarding Management Report"] = {
	"filters": [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		}
	],

	"initial_depth": 1,

	onload: function(report) {
		// Export PDF button
		report.page.add_inner_button('Export PDF', function() {
			generate_report_pdf(report);
		}, 'Export');

		// Standard Excel Export
		report.page.add_inner_button('Export to Excel', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_excel?report_name=Forwarding Management Report&filters=${query}`;
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

		// Bold customer name on parent rows
		if (column.fieldname === "customer" && data && data.indent === 0 && data.customer) {
			value = `<strong>${value}</strong>`;
		}

		// Color-code status on child rows
		if (column.fieldname === "status" && data && data.indent === 1) {
			let color = "gray";
			if (data.status === "In Progress") color = "blue";
			else if (data.status === "Delivered") color = "green";
			else if (data.status === "Completed") color = "green";
			else if (data.status === "Draft") color = "orange";

			value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		}

		return value;
	}
};

function generate_report_pdf(report) {
	const filters = report.get_filter_values(true);

	frappe.show_alert({
		message: 'Generating PDF...',
		indicator: 'blue'
	});

	frappe.call({
		method: 'freightmas.forwarding_service.report.forwarding_management_report.forwarding_management_report.generate_management_report_pdf',
		args: {
			filters: JSON.stringify(filters)
		},
		callback: function(response) {
			if (response.message) {
				const pdf_url = 'data:application/pdf;base64,' + response.message.pdf_content;
				const link = document.createElement('a');
				link.href = pdf_url;
				link.download = response.message.filename;
				document.body.appendChild(link);
				link.click();
				document.body.removeChild(link);

				frappe.show_alert({
					message: 'PDF generated successfully!',
					indicator: 'green'
				});
			} else {
				frappe.msgprint('Error generating PDF. Please try again.');
			}
		},
		error: function(error) {
			console.error('PDF Generation Error:', error);
			frappe.msgprint('Error generating PDF. Please contact your system administrator.');
		}
	});
}
