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

		// Add PDF and Email export buttons for each customer row
		if (column.fieldname === "customer" && data.customer) {
			value += ` <button class="btn btn-xs btn-primary customer-pdf-btn" 
						data-customer="${data.customer}" 
						style="margin-left: 10px; font-size: 10px; padding: 2px 6px;"
						title="Export Consolidated Tracking PDF">
						📄 PDF
					</button>`;
			value += ` <button class="btn btn-xs btn-success customer-email-btn" 
						data-customer="${data.customer}" 
						style="margin-left: 5px; font-size: 10px; padding: 2px 6px;"
						title="Email Consolidated Tracking Report">
						📧 Email
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

// Function to show email dialog for specific customer
function show_customer_email_dialog(customer) {
	// Get customer email
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Customer',
			filters: {'name': customer},
			fieldname: ['email_id', 'customer_name']
		},
		callback: function(response) {
			let customer_data = response.message || {};
			let customer_email = customer_data.email_id || '';
			let customer_name = customer_data.customer_name || customer;
			
			// Create email dialog
			let email_dialog = new frappe.ui.Dialog({
				title: `Email Tracking Report - ${customer_name}`,
				fields: [
					{
						fieldname: 'to_email',
						label: 'To Email',
						fieldtype: 'Data',
						reqd: 1,
						default: customer_email,
						description: 'Primary recipient email address'
					},
					{
						fieldname: 'cc_emails',
						label: 'CC Emails',
						fieldtype: 'Data',
						description: 'Additional recipients (comma separated)'
					},
					{
						fieldname: 'subject',
						label: 'Subject',
						fieldtype: 'Data',
						reqd: 1,
						default: `Consolidated Tracking Report - ${customer_name}`
					},
					{
						fieldname: 'message',
						label: 'Message',
						fieldtype: 'Text Editor',
						reqd: 1,
						default: `Dear ${customer_name},<br><br>Please find attached your consolidated tracking report for active shipments.<br><br>Best regards,<br>FreightMas Team<br><br>Please contact your account manager if you need clarity on anything.`
					},
					{
						fieldname: 'attach_pdf',
						label: 'Attach PDF Report',
						fieldtype: 'Check',
						default: 1
					}
				],
				primary_action_label: 'Send Email',
				primary_action: function(values) {
					if (values.to_email) {
						send_customer_email(customer, values);
						email_dialog.hide();
					}
				}
			});
			
			email_dialog.show();
		}
	});
}

// Function to send email using server method
function send_customer_email(customer, email_data) {
	// Show loading message
	frappe.show_alert({
		message: `Sending email to ${email_data.to_email}...`,
		indicator: 'blue'
	});

	// Call server method to send email
	frappe.call({
		method: 'freightmas.forwarding_service.report.fwjb_consolidated_tracking.fwjb_consolidated_tracking.send_customer_tracking_email',
		args: {
			customer: customer,
			to_email: email_data.to_email,
			subject: email_data.subject,
			message: email_data.message,
			cc_emails: email_data.cc_emails,
			attach_pdf: email_data.attach_pdf
		},
		callback: function(response) {
			if (response.message && response.message.success) {
				frappe.show_alert({
					message: response.message.message,
					indicator: 'green'
				});
			} else {
				frappe.msgprint({
					title: 'Email Error',
					message: response.message?.message || 'Failed to send email',
					indicator: 'red'
				});
			}
		},
		error: function(error) {
			console.error('Email sending error:', error);
			frappe.msgprint({
				title: 'Email Error',
				message: 'Failed to send email. Please contact your system administrator.',
				indicator: 'red'
			});
		}
	});
}
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

// Apply event handlers for inline PDF and Email buttons
$(document).ready(function() {
	$(document).on('click', '.customer-pdf-btn', function(e) {
		e.stopPropagation();
		const customer = $(this).data('customer');
		if (customer) {
			generate_customer_pdf(customer);
		}
	});
	
	$(document).on('click', '.customer-email-btn', function(e) {
		e.stopPropagation();
		const customer = $(this).data('customer');
		if (customer) {
			show_customer_email_dialog(customer);
		}
	});
});