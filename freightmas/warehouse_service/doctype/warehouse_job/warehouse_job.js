// Copyright (c) 2025, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job', {
	refresh: function(frm) {
		// Load transactions HTML
		if (!frm.is_new()) {
			frm.call('get_transactions_html').then(r => {
				if (r.message) {
					frm.set_df_property('transactions_html', 'options', r.message);
				}
			});
		}
		
		// Add Create button with Customer Goods Receipt and Dispatch options
		if (!frm.is_new() && frm.doc.status !== "Completed") {
			frm.add_custom_button(__('Customer Goods Receipt'), function() {
				frappe.new_doc('Customer Goods Receipt', {
					warehouse_job: frm.doc.name,
					customer: frm.doc.customer,
					receipt_date: frappe.datetime.get_today()
				});
			}, __('Create'));
			
			frm.add_custom_button(__('Customer Goods Dispatch'), function() {
				frappe.new_doc('Customer Goods Dispatch', {
					warehouse_job: frm.doc.name,
					customer: frm.doc.customer,
					dispatch_date: frappe.datetime.get_today()
				});
			}, __('Create'));
			
			// Add Fetch Handling Charges button
			frm.add_custom_button(__('Fetch Handling Charges'), function() {
				frappe.call({
					method: 'fetch_handling_charges',
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({
								message: r.message.message,
								indicator: 'green'
							});
							frm.refresh_field('handling_charges');
							frm.dirty();
						}
					}
				});
			}, __('Actions'));
			
			// Add Create Sales Invoice button
			frm.add_custom_button(__('Create Sales Invoice'), function() {
				create_sales_invoice_from_charges(frm);
			}, __('Create'));
		}
		
		// Add Calculate Storage Charges button
		if (!frm.is_new()) {
			frm.add_custom_button(__('Calculate Storage Charges'), function() {
				calculate_storage_charges_dialog(frm);
			}, __('Actions'));
		}
		
		// Add custom buttons for workflow actions
		if (frm.doc.docstatus === 1 && frm.doc.status === "Active") {
			frm.add_custom_button(__('Mark as Completed'), function() {
				frappe.call({
					method: 'frappe.client.set_value',
					args: {
						doctype: 'Warehouse Job',
						name: frm.doc.name,
						fieldname: 'status',
						value: 'Completed'
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			});
		}
	},
	
	fiscal_year: function(frm) {
		// Auto-populate job dates from fiscal year
		if (frm.doc.fiscal_year && frm.is_new()) {
			frappe.db.get_value('Fiscal Year', frm.doc.fiscal_year, ['year_start_date', 'year_end_date'], (r) => {
				if (r) {
					// Set job start date to today or fiscal year start (whichever is later)
					let today = frappe.datetime.get_today();
					let fy_start = r.year_start_date;
					frm.set_value('job_start_date', frappe.datetime.str_to_obj(today) > frappe.datetime.str_to_obj(fy_start) ? today : fy_start);
					
					// Set job end date to fiscal year end
					frm.set_value('job_end_date', r.year_end_date);
				}
			});
		}
	},
	
	job_start_date: function(frm) {
		frm.trigger('calculate_validity');
	},
	
	job_end_date: function(frm) {
		frm.trigger('calculate_validity');
	},
	
	calculate_validity: function(frm) {
		if (frm.doc.job_start_date && frm.doc.job_end_date) {
			let days = frappe.datetime.get_day_diff(frm.doc.job_end_date, frm.doc.job_start_date) + 1;
			frm.set_value('job_validity_days', days);
		}
	}
});

// ========================================
// CREATE SALES INVOICE FROM HANDLING CHARGES
// ========================================

function create_sales_invoice_from_charges(frm) {
	// Combine handling and storage charges
	const handling_rows = (frm.doc.handling_charges || []).map(row => ({
		...row,
		charge_type: 'Handling',
		item_description: row.description || row.handling_activity_type || 'Handling Service',
		item_code: row.handling_activity_type || 'Handling Service'
	}));
	
	const storage_rows = (frm.doc.storage_charges || []).map(row => ({
		...row,
		charge_type: 'Storage',
		customer: frm.doc.customer, // Storage charges use job customer
		activity_date: row.end_date,
		quantity: row.quantity,
		rate: row.amount / row.quantity, // Calculate rate from amount
		item_description: `Storage: ${row.uom} (${row.storage_days} days)`,
		item_code: 'Storage Service'
	}));
	
	const all_rows = [...handling_rows, ...storage_rows];
	const eligible_rows = all_rows.filter(row => 
		row.amount && row.customer && !row.is_invoiced
	);

	if (!eligible_rows.length) {
		frappe.msgprint(__("No eligible charges found for invoicing."));
		return;
	}

	let selected_customer = eligible_rows[0].customer;

	const get_unique_customers = () => [...new Set(eligible_rows.map(r => r.customer))];

	const render_dialog_ui = (dialog, customer) => {
		const customers = get_unique_customers();
		const rows = customer ? eligible_rows.filter(r => r.customer === customer) : eligible_rows;

		const customer_filter = `
			<div style="margin-bottom: 15px;">
				<label for="customer-filter" style="font-weight: bold; margin-bottom: 5px; display: block;">Customer:</label>
				<select id="customer-filter" class="customer-filter form-control">
					${customers.map(c => `<option value="${c}" ${c === customer ? 'selected' : ''}>${c}</option>`).join('')}
				</select>
			</div>
		`;

		const select_all_html = `
			<div style="margin-bottom: 10px;">
				<label>
					<input type="checkbox" id="select-all-charges" class="select-all-charges"> 
					<strong>Select All</strong>
				</label>
			</div>
		`;

		const table_html = `
			<table class="table table-bordered" style="margin-top: 10px;">
				<thead>
					<tr>
						<th style="width: 40px;"></th>
						<th>Type</th>
						<th>Date</th>
						<th>Activity/UOM</th>
						<th>Description</th>
						<th>Qty</th>
						<th>Rate</th>
						<th>Amount</th>
					</tr>
				</thead>
				<tbody>
					${rows.map(row => `
						<tr>
							<td>
								<input type="checkbox" class="charge-row-check" data-row-name="${row.name}" data-charge-type="${row.charge_type}">
							</td>
							<td><span class="badge badge-${row.charge_type === 'Storage' ? 'info' : 'primary'}">${row.charge_type}</span></td>
							<td>${frappe.datetime.str_to_user(row.activity_date) || '-'}</td>
							<td>${row.charge_type === 'Storage' ? row.uom : (row.handling_activity_type || '-')}</td>
							<td>${row.item_description || '-'}</td>
							<td>${row.quantity || 0}</td>
							<td>${format_currency(row.rate || 0)}</td>
							<td>${format_currency(row.amount || 0)}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;

		const full_html = customer_filter + select_all_html + table_html;
		dialog.fields_dict.charge_rows_html.$wrapper.html(full_html);

		// Customer filter handler
		dialog.$wrapper.find('.customer-filter').off('change').on('change', function() {
			selected_customer = this.value;
			render_dialog_ui(dialog, selected_customer);
		});

		// Select all checkbox handler
		dialog.$wrapper.find('#select-all-charges').on('change', function() {
			const isChecked = this.checked;
			dialog.$wrapper.find('.charge-row-check').prop('checked', isChecked);
		});

		// Individual checkbox handler
		dialog.$wrapper.find('.charge-row-check').on('change', function() {
			const total = dialog.$wrapper.find('.charge-row-check').length;
			const checked = dialog.$wrapper.find('.charge-row-check:checked').length;
			dialog.$wrapper.find('#select-all-charges').prop('checked', total === checked);
		});
	};

	const dialog = new frappe.ui.Dialog({
		title: __('Select Charges for Sales Invoice'),
		size: 'large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'charge_rows_html',
				options: ''
			}
		],
		primary_action_label: __('Create Sales Invoice'),
		primary_action() {
			const selected = Array.from(
				dialog.$wrapper.find('.charge-row-check:checked')
			).map(el => ({
				name: el.dataset.rowName,
				charge_type: el.dataset.chargeType
			}));

			if (!selected.length) {
				frappe.msgprint(__("Please select at least one charge."));
				return;
			}

			const selected_names = selected.map(s => s.name);
			const selected_rows = eligible_rows.filter(r => selected_names.includes(r.name));
			const unique_customers = [...new Set(selected_rows.map(r => r.customer))];

			if (unique_customers.length > 1) {
				frappe.msgprint(__("You can only create an invoice for one customer at a time."));
				return;
			}

			frappe.call({
				method: "freightmas.warehouse_service.doctype.warehouse_job.warehouse_job.create_sales_invoice_with_rows",
				args: {
					docname: frm.doc.name,
					row_names: selected
				},
				callback(r) {
					if (r.message) {
						frappe.msgprint({
							title: __('Sales Invoice Created'),
							message: __('Sales Invoice {0} has been created successfully', [r.message]),
							indicator: 'green'
						});
						
						frappe.set_route("Form", "Sales Invoice", r.message);
						frm.reload_doc();
						dialog.hide();
					}
				}
		});
	}
});

	dialog.show();
	render_dialog_ui(dialog, selected_customer);
}

// Calculate Storage Charges Dialog
function calculate_storage_charges_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __('Calculate Storage Charges'),
		fields: [
			{
				label: __('Start Date'),
				fieldname: 'start_date',
				fieldtype: 'Date',
				reqd: 1,
				default: frappe.datetime.month_start()
			},
			{
				label: __('End Date'),
				fieldname: 'end_date',
				fieldtype: 'Date',
				reqd: 1,
				default: frappe.datetime.month_end()
			}
		],
		primary_action_label: __('Calculate'),
		primary_action(values) {
			frappe.call({
				method: 'freightmas.warehouse_service.doctype.warehouse_job.warehouse_job.calculate_monthly_storage_for_job',
				args: {
					docname: frm.doc.name,
					start_date: values.start_date,
					end_date: values.end_date
				},
				callback: function(r) {
					if (r.message) {
						frm.reload_doc();
						d.hide();
					}
				}
			});
		}
	});
	
	d.show();
}
