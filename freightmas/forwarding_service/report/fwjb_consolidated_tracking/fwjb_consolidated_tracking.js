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

		// Add action links for each customer row
		if (column.fieldname === "customer" && data.customer) {
			value += `
				<span class="customer-actions" style="margin-left: 15px; font-size: 11px;">
					<a href="#" class="action-link customer-email-link" 
					   data-customer="${data.customer}" 
					   style="color: #5e64ff; text-decoration: none; margin-right: 8px;"
					   title="Send tracking email to customer">
						Send Email
					</a>
					<span style="color: #ccc; margin-right: 8px;">|</span>
					<a href="#" class="action-link customer-pdf-link" 
					   data-customer="${data.customer}" 
					   style="color: #5e64ff; text-decoration: none; margin-right: 8px;"
					   title="Export consolidated tracking PDF">
						Export PDF
					</a>
					<span style="color: #ccc; margin-right: 8px;">|</span>
					<a href="/app/forwarding-job?customer=${encodeURIComponent(data.customer)}" 
					   class="action-link customer-jobs-link" 
					   style="color: #5e64ff; text-decoration: none;"
					   title="View all jobs for this customer">
						View Jobs
					</a>
				</span>
			`;
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
	// Get customer email and tracking settings
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Customer',
			filters: {'name': customer},
			fieldname: ['email_id', 'customer_name', 'tracking_email', 'tracking_cc_emails', 'tracking_email_enabled']
		},
		callback: function(response) {
			let customer_data = response.message || {};
			
			// Check if tracking emails are enabled
			if (customer_data.tracking_email_enabled === 0) {
				frappe.msgprint({
					title: 'Tracking Emails Disabled',
					message: `Tracking emails are disabled for ${customer_data.customer_name || customer}. Please enable them in the Customer record first.`,
					indicator: 'orange'
				});
				return;
			}
			
			// Use tracking_email first, fallback to email_id
			let primary_email = customer_data.tracking_email || customer_data.email_id || '';
			let cc_emails = customer_data.tracking_cc_emails || '';
			let customer_name = customer_data.customer_name || customer;
			
			// Create email dialog
			let email_dialog = new frappe.ui.Dialog({
				title: `Email Tracking Report - ${customer_name}`,
				fields: [
					{
						fieldname: 'to_email',
						label: 'To Email',
						fieldtype: 'Data',
						options: 'Email',
						reqd: 1,
						default: primary_email,
						description: 'Primary recipient email address'
					},
					{
						fieldname: 'cc_emails',
						label: 'CC Emails',
						fieldtype: 'Small Text',
						default: cc_emails,
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
						fieldname: 'email_template',
						label: 'Load Template',
						fieldtype: 'Link',
						options: 'Email Template',
						description: 'Optional: Select a template to load',
						change: function() {
							let template_name = email_dialog.get_value('email_template');
							if (template_name) {
								load_email_template(template_name, customer_name, email_dialog);
							}
						}
					},
					{
						fieldname: 'message',
						label: 'Message',
						fieldtype: 'Text Editor',
						reqd: 1,
						default: `Dear ${customer_name},<br><br>Please find attached your consolidated tracking report for active jobs.<br><br>Best regards,<br>`
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
					// Validate email formats
					if (!validate_email_format(values.to_email)) {
						frappe.msgprint('Please enter a valid email address');
						return;
					}
					
					// Validate CC emails if provided
					if (values.cc_emails && !validate_cc_emails(values.cc_emails)) {
						frappe.msgprint('Please enter valid CC email addresses (comma separated)');
						return;
					}
					
					send_customer_email(customer, values);
					email_dialog.hide();
				}
			});
			
			email_dialog.show();
		}
	});
}

// Email validation helper functions
function validate_email_format(email) {
	const email_regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
	return email_regex.test(email);
}

function validate_cc_emails(cc_emails) {
	if (!cc_emails.trim()) return true;
	const emails = cc_emails.split(',').map(email => email.trim());
	return emails.every(email => validate_email_format(email));
}

// Function to load email template content
function load_email_template(template_name, customer_name, dialog) {
	frappe.call({
		method: 'frappe.email.doctype.email_template.email_template.get_email_template',
		args: {
			template_name: template_name,
			doc: {
				'name': customer_name,
				'customer_name': customer_name
			}
		},
		callback: function(response) {
			if (response.message) {
				// Update dialog fields with template content
				if (response.message.subject) {
					dialog.set_value('subject', response.message.subject);
				}
				if (response.message.message) {
					dialog.set_value('message', response.message.message);
				}
				
				frappe.show_alert({
					message: `Template "${template_name}" loaded successfully`,
					indicator: 'green'
				});
			}
		},
		error: function(error) {
			console.error('Template loading error:', error);
			// Fallback: Get template manually
			frappe.db.get_doc('Email Template', template_name)
				.then(template => {
					if (template.subject) {
						dialog.set_value('subject', template.subject);
					}
					if (template.response) {
						// Process basic variables
						let message = template.response.replace(/{{ customer_name }}/g, customer_name);
						dialog.set_value('message', message);
					}
					frappe.show_alert({
						message: `Template "${template_name}" loaded`,
						indicator: 'green'
					});
				})
				.catch(err => {
					frappe.show_alert({
						message: 'Error loading template',
						indicator: 'red'
					});
				});
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

// Apply event handlers for inline action links
$(document).ready(function() {
	// Handle PDF export links
	$(document).on('click', '.customer-pdf-link', function(e) {
		e.preventDefault();
		e.stopPropagation();
		const customer = $(this).data('customer');
		if (customer) {
			generate_customer_pdf(customer);
		}
	});
	
	// Handle Email links
	$(document).on('click', '.customer-email-link', function(e) {
		e.preventDefault();
		e.stopPropagation();
		const customer = $(this).data('customer');
		if (customer) {
			show_customer_email_dialog(customer);
		}
	});
	
	// Add hover effects for action links
	$(document).on('mouseenter', '.action-link', function() {
		$(this).css({
			'color': '#4c52cc',
			'text-decoration': 'underline'
		});
	});
	
	$(document).on('mouseleave', '.action-link', function() {
		$(this).css({
			'color': '#5e64ff',
			'text-decoration': 'none'
		});
	});
});