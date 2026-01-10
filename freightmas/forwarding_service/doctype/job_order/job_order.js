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

// Child table events for items
frappe.ui.form.on('Job Order Items', {
	items_add: function(frm, cdt, cdn) {
		// Prevent manual addition of items
		frappe.model.clear_table(frm.doc, 'items');
		frm.refresh_field('items');
		frappe.msgprint(__('Items are automatically loaded from the Quotation. Please select a Quotation Reference.'));
	}
});

// Child table events for documents checklist
frappe.ui.form.on('Job Order Documents Checklist', {
	is_received: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.is_received && !row.received_date) {
			frappe.model.set_value(cdt, cdn, 'received_date', frappe.datetime.nowdate());
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
				frm.set_value('cargo_description', quotation.cargo_description);
				frm.set_value('currency', quotation.currency);
				
				// Clear and populate items
				frm.clear_table('items');
				
				if (quotation.items && quotation.items.length > 0) {
					quotation.items.forEach(function(item) {
						let child = frm.add_child('items');
						child.item_code = item.item_code;
						child.item_name = item.item_name;
						child.description = item.description;
						child.qty = item.qty;
						child.uom = item.uom;
						child.rate = item.rate;
						child.amount = item.amount;
					});
					
					frm.refresh_field('items');
					calculate_total(frm);
					
					frappe.show_alert({
						message: __('Loaded {0} items from Quotation', [quotation.items.length]),
						indicator: 'green'
					}, 5);
				}
			}
		}
	});
}

function calculate_total(frm) {
	let total = 0;
	
	if (frm.doc.items) {
		frm.doc.items.forEach(function(item) {
			total += flt(item.amount);
		});
	}
	
	frm.set_value('total_quoted_amount', total);
}

function create_forwarding_job_from_order(frm) {
	frappe.confirm(
		__('Are you sure you want to create a Forwarding Job from this Job Order?<br><br>This will:<br>- Create a new Forwarding Job<br>- Copy all service charges and documents<br>- Link the Job Order to the Forwarding Job'),
		function() {
			// User confirmed
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
						
						// Offer to open the new Forwarding Job
						frappe.show_alert({
							message: __('Forwarding Job {0} created successfully!', [r.message]),
							indicator: 'green'
						}, 5);
						
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
