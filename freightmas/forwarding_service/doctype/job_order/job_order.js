// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Order', {
	refresh: function(frm) {
		// Show appropriate buttons based on document state
		if (!frm.is_new()) {
			// Button to view linked quotation
			if (frm.doc.quotation_reference) {
				frm.add_custom_button(__('View Quotation'), function() {
					frappe.set_route('Form', 'Quotation', frm.doc.quotation_reference);
				}, __('View'));
			}
			
			// Button to create Forwarding Job (only if submitted and not already converted)
			if (frm.doc.docstatus === 1 && !frm.doc.forwarding_job_reference) {
				frm.add_custom_button(__('Create Forwarding Job'), function() {
					create_forwarding_job_from_order(frm);
				}, __('Create')).addClass('btn-primary');
			}
			
			// Button to view created Forwarding Job
			if (frm.doc.forwarding_job_reference) {
				frm.add_custom_button(__('View Forwarding Job'), function() {
					frappe.set_route('Form', 'Forwarding Job', frm.doc.forwarding_job_reference);
				}, __('View'));
				
				// Show info message
				frm.dashboard.add_comment(
					__('This Job Order has been converted to Forwarding Job {0}', [frm.doc.forwarding_job_reference]),
					'green',
					true
				);
			}
		}
		
		// Add indicator for conversion status
		if (frm.doc.docstatus === 1) {
			if (frm.doc.forwarding_job_reference) {
				frm.dashboard.set_headline_alert(
					__('Converted to Forwarding Job: {0}', [frm.doc.forwarding_job_reference]),
					'green'
				);
			} else {
				frm.dashboard.set_headline_alert(
					__('Ready to Convert to Forwarding Job'),
					'blue'
				);
			}
		}
	},
	
	quotation_reference: function(frm) {
		// When quotation is selected, fetch and populate items automatically
		if (frm.doc.quotation_reference && frm.is_new()) {
			load_quotation_data(frm);
		}
	},
	
	before_save: function(frm) {
		// Calculate totals before saving
		calculate_total(frm);
	}
});

// Child table events for job_order_charges
frappe.ui.form.on('Job Order Charges', {
	qty: function(frm, cdt, cdn) {
		calculate_row_amounts(frm, cdt, cdn);
	},
	
	sell_rate: function(frm, cdt, cdn) {
		calculate_row_amounts(frm, cdt, cdn);
	},
	
	buy_rate: function(frm, cdt, cdn) {
		calculate_row_amounts(frm, cdt, cdn);
	}
});

// Child table events for documents checklist
frappe.ui.form.on('Forwarding Documents Checklist', {
	is_submitted: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.is_submitted && !row.date_submitted) {
			frappe.model.set_value(cdt, cdn, 'date_submitted', frappe.datetime.nowdate());
		}
	},
	is_verified: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.is_verified && !row.date_verified) {
			frappe.model.set_value(cdt, cdn, 'date_verified', frappe.datetime.nowdate());
		}
	}
});

// ===================================
// Helper Functions
// ===================================

function load_quotation_data(frm) {
	if (!frm.doc.quotation_reference) return;
	
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Quotation',
			name: frm.doc.quotation_reference
		},
		callback: function(r) {
			if (r.message) {
				let quotation = r.message;
				
				// Populate service details
				frm.set_value('direction', quotation.direction);
				frm.set_value('shipment_mode', quotation.shipment_mode);
				frm.set_value('origin_port', quotation.origin_port);
				frm.set_value('destination_port', quotation.destination_port);
				frm.set_value('incoterms', quotation.incoterms);
				frm.set_value('job_description', quotation.job_description);
				frm.set_value('currency', quotation.currency);
				
				// Clear and populate job_order_charges
				frm.clear_table('job_order_charges');
				
				if (quotation.items && quotation.items.length > 0) {
					quotation.items.forEach(function(item) {
						let child = frm.add_child('job_order_charges');
						child.charge = item.item_code;
						child.description = item.description || item.item_name;
						child.qty = item.qty || 1;
						child.sell_rate = item.rate || 0;
						child.customer = frm.doc.customer;
						
						// Copy cost fields if available
						if (item.buy_rate) {
							child.buy_rate = item.buy_rate;
						}
						if (item.supplier) {
							child.supplier = item.supplier;
						}
						
						// Calculate amounts
						child.revenue_amount = (child.qty || 0) * (child.sell_rate || 0);
						child.cost_amount = (child.qty || 0) * (child.buy_rate || 0);
					});
					
					frm.refresh_field('job_order_charges');
					calculate_total(frm);
					
					frappe.show_alert({
						message: __('Loaded {0} charges from Quotation', [quotation.items.length]),
						indicator: 'green'
					}, 5);
				}
			}
		}
	});
}

function calculate_total(frm) {
	let total = 0;
	
	if (frm.doc.job_order_charges) {
		frm.doc.job_order_charges.forEach(function(charge) {
			total += flt(charge.revenue_amount || 0);
		});
	}
	
	frm.set_value('total_quoted_amount', total);
}

function calculate_row_amounts(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	
	// Calculate revenue amount
	row.revenue_amount = flt(row.qty || 0) * flt(row.sell_rate || 0);
	
	// Calculate cost amount
	row.cost_amount = flt(row.qty || 0) * flt(row.buy_rate || 0);
	
	frm.refresh_field('job_order_charges');
	calculate_total(frm);
}

function create_forwarding_job_from_order(frm) {
	frappe.confirm(
		__('Create Forwarding Job from this Job Order?<br><br>This will create and save a complete Forwarding Job linked to this Job Order.'),
		function() {
			frappe.call({
				method: 'freightmas.forwarding_service.doctype.job_order.job_order.create_forwarding_job',
				args: {
					job_order_name: frm.doc.name
				},
				freeze: true,
				freeze_message: __('Creating Forwarding Job...'),
				callback: function(r) {
					if (r.message) {
						frm.reload_doc();
						
						frappe.show_alert({
							message: __('Forwarding Job {0} created successfully!', [r.message]),
							indicator: 'green'
						}, 5);
						
						// Offer to open the new Forwarding Job
						setTimeout(function() {
							frappe.confirm(
								__('Would you like to open the newly created Forwarding Job?'),
								function() {
									frappe.set_route('Form', 'Forwarding Job', r.message);
								}
							);
						}, 1000);
					}
				}
			});
		}
	);
}
