// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["FWJB Consolidated Tracking"] = {
	"filters": [],

	onload: function(report) {
		// Add Export PDF button
		report.page.add_inner_button('Export PDF', function() {
			show_customer_pdf_dialog(report);
		}, 'Export');

		// Standard Excel Export
		report.page.add_inner_button('Export to Excel', function() {
			const filters = report.get_filter_values(true);
			const query = encodeURIComponent(JSON.stringify(filters));
			const url = `/api/method/freightmas.api.export_report_to_excel?report_name=FWJB Consolidated Tracking&filters=${query}`;
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

		// Add PDF export button for each customer row
		if (column.fieldname === "customer" && data.customer) {
			value += ` <button class="btn btn-xs btn-primary customer-pdf-btn" 
						data-customer="${data.customer}" 
						style="margin-left: 10px; font-size: 10px; padding: 2px 6px;"
						title="Export Consolidated Tracking PDF">
					📄 PDF
					</button>`;
		}

		return value;
	}
};

// Function to show customer selection dialog for PDF export
function show_customer_pdf_dialog(report) {
	const data = report.data || [];
	if (data.length === 0) {
		frappe.msgprint('No customers found in the current filter criteria.');
		return;
	}

	// Create options from current data
	const customer_options = data.map(row => row.customer).filter(Boolean);

	if (customer_options.length === 0) {
		frappe.msgprint('No customers available for PDF export.');
		return;
	}

	let dialog = new frappe.ui.Dialog({
		title: 'Export Consolidated Tracking PDF',
		fields: [
			{
				fieldname: 'customer',
				label: 'Select Customer',
				fieldtype: 'Select',
				options: customer_options,
				reqd: 1,
				description: 'Choose a customer to generate their consolidated tracking report'
			}
		],
		primary_action_label: 'Generate PDF',
		primary_action: function(values) {
			if (values.customer) {
				generate_customer_pdf(values.customer);
				dialog.hide();
			}
		}
	});

	dialog.show();
}

// Function to generate PDF for specific customer using print format
function generate_customer_pdf(customer) {
	// Show loading message
	frappe.show_alert({
		message: `Generating consolidated tracking PDF for ${customer}...`,
		indicator: 'blue'
	});

	// Call server method to generate PDF using print format
	frappe.call({
		method: 'freightmas.forwarding_service.report.fwjb_consolidated_tracking.fwjb_consolidated_tracking.generate_customer_tracking_pdf',
		args: {
			customer: customer
		},
		callback: function(response) {
			if (response.message) {
				// Create download link for PDF
				const pdf_url = 'data:application/pdf;base64,' + response.message.pdf_content;
				const link = document.createElement('a');
				link.href = pdf_url;
				link.download = response.message.filename;
				document.body.appendChild(link);
				link.click();
				document.body.removeChild(link);

				frappe.show_alert({
					message: `PDF generated successfully for ${customer}!`,
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

// Apply event handlers for inline PDF buttons
$(document).ready(function() {
	$(document).on('click', '.customer-pdf-btn', function(e) {
		e.stopPropagation();
		const customer = $(this).data('customer');
		if (customer) {
			generate_customer_pdf(customer);
		}
	});
});