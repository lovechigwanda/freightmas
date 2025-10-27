// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// For license information, please see license.txt

// ==========================================================
// Forwarding Job - Client Script
// Handles currency logic, charge calculations, invoicing,
// and cargo count summary
// ==========================================================

frappe.ui.form.on('Forwarding Job', {
    refresh: function(frm) {
        // ========================================
        // ADD PORTAL BUTTONS UNDER "VIEW" DROPDOWN
        // ========================================
        if (frm.doc.share_with_road_freight && !frm.is_new()) {
            
            // Add "Open Web Portal" button
            frm.page.add_inner_button(__('Open Web Portal'), function() {
                const url = `${window.location.origin}/truck_portal?job=${frm.doc.name}`;
                window.open(url, '_blank');
            }, __('View'));
            
            // Add "Copy Portal Link" button
            frm.page.add_inner_button(__('Copy Portal Link'), function() {
                const url = `${window.location.origin}/truck_portal?job=${frm.doc.name}`;
                
                // Copy to clipboard
                navigator.clipboard.writeText(url).then(() => {
                    frappe.show_alert({
                        message: __('Portal link copied to clipboard! 📋'),
                        indicator: 'green'
                    }, 5);
                }).catch(() => {
                    // Fallback for older browsers
                    const tempInput = document.createElement('input');
                    tempInput.value = url;
                    document.body.appendChild(tempInput);
                    tempInput.select();
                    document.execCommand('copy');
                    document.body.removeChild(tempInput);
                    
                    frappe.show_alert({
                        message: __('Portal link copied! 📋'),
                        indicator: 'green'
                    }, 5);
                });
                
                // Show the link in a dialog
                frappe.msgprint({
                    title: __('🚛 Web Portal Link'),
                    indicator: 'blue',
                    message: `
                        <div style="padding: 15px;">
                            <p style="margin-bottom: 15px; font-size: 14px;">
                                <strong>Share this link with road freight suppliers:</strong>
                            </p>
                            <div style="background: #f8f9fb; padding: 15px; border-radius: 8px; border: 2px solid #667eea; font-family: monospace; word-break: break-all; font-size: 13px; margin-bottom: 15px;">
                                ${url}
                            </div>
                            <div style="background: #e0e7ff; padding: 12px; border-radius: 6px; border-left: 4px solid #667eea;">
                                <p style="margin: 0; font-size: 13px; color: #1e293b;">
                                    <i class="fa fa-info-circle"></i> 
                                    <strong>Note:</strong> Users must be logged in to access the portal.
                                </p>
                            </div>
                        </div>
                    `,
                    primary_action_label: __('Open Portal'),
                    primary_action: () => {
                        window.open(url, '_blank');
                    }
                });
            }, __('View'));
            
            // Add separator line in dropdown for better organization
            frm.page.add_inner_button(__('─────────'), function() {
                // This is just a visual separator, does nothing
            }, __('View')).prop('disabled', true).css({
                'pointer-events': 'none',
                'opacity': '0.5',
                'cursor': 'default'
            });
        }
        
        // ========================================
        // SHOW INFO MESSAGE WHEN SHARING IS ENABLED
        // ========================================
        if (frm.doc.share_with_road_freight && !frm.is_new()) {
            frm.dashboard.add_comment(
                `<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                    <i class="fa fa-globe" style="font-size: 18px; margin-right: 8px;"></i>
                    <strong>Web Portal Active</strong> - 
                    This job is accessible to road freight suppliers via the web portal.
                    <a href="${window.location.origin}/truck_portal?job=${frm.doc.name}" 
                       target="_blank" 
                       style="color: white; text-decoration: underline; margin-left: 10px;">
                        View Portal →
                    </a>
                </div>`,
                'blue',
                true
            );
        }
        
        // ========================================
        // YOUR EXISTING CODE BELOW
        // ========================================
        calculate_costing_totals(frm);
        calculate_actual_totals(frm);
        
        // Toggle base fields for both costing and actuals
        toggle_base_fields(frm);
        
        // Update currency labels for both costing and actuals
        update_currency_labels(frm);
        update_cargo_count_forwarding(frm);

        // Add the missing custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Create Sales Invoice'), function() {
                create_sales_invoice_from_charges(frm);
            }, __('Create'));

            frm.add_custom_button(__('Create Purchase Invoice'), function() {
                create_purchase_invoice_from_charges(frm);
            }, __('Create'));

            // --- Add View > Cost Sheet button ---
            frm.add_custom_button(__('Cost Sheet'), function() {
                window.open(
                    `/printview?doctype=Forwarding%20Job&name=${frm.doc.name}&format=Forwarding%20Job%20Cost%20Sheet&no_letterhead=1`,
                    '_blank'
                );
            }, __('View'));
            // --- End View > Cost Sheet button ---
        }
    },
    
    validate(frm) {
        calculate_costing_totals(frm);
        calculate_actual_totals(frm);
    },

    currency(frm) {
        if (frm.doc.currency && frm.doc.base_currency && frm.doc.currency !== frm.doc.base_currency) {
            frappe.call({
                method: "erpnext.setup.utils.get_exchange_rate",
                args: {
                    from_currency: frm.doc.currency,
                    to_currency: frm.doc.base_currency
                },
                callback(r) {
                    if (r.message) {
                        set_main_value_safe(frm, "conversion_rate", r.message);
                        calculate_costing_totals(frm);
                        calculate_actual_totals(frm);
                        toggle_base_fields(frm);
                    }
                }
            });
        } else {
            set_main_value_safe(frm, "conversion_rate", 1.0);
            calculate_costing_totals(frm);
            calculate_actual_totals(frm);
            toggle_base_fields(frm);
        }

        update_currency_labels(frm);
    },

    conversion_rate(frm) {
        calculate_costing_totals(frm);
        calculate_actual_totals(frm);
    },

    base_currency(frm) {
        update_currency_labels(frm);
        toggle_base_fields(frm);
    },

    before_save(frm) {
        const tracking = frm.doc.forwarding_tracking;
        if (tracking && tracking.length > 0) {
            const last = tracking[tracking.length - 1];

            set_main_value_safe(frm, 'current_comment', last.comment);
            set_main_value_safe(frm, 'last_updated_on', last.updated_on);
            set_main_value_safe(frm, 'last_updated_by', last.updated_by);
        }
    },

    fetch_from_quotation(frm) {
        open_fetch_charges_from_quotation_dialog(frm);
    },
    
    share_with_road_freight: function(frm) {
        // Show message when checkbox is checked/unchecked
        if (frm.doc.share_with_road_freight) {
            frappe.show_alert({
                message: __('🌐 Job will be accessible via web portal after saving'),
                indicator: 'blue'
            }, 5);
        } else {
            frappe.show_alert({
                message: __('Web portal access will be disabled after saving'),
                indicator: 'orange'
            }, 5);
        }
    }
});

// ==========================================================
// Charge Row Calculation Logic
// ==========================================================

function update_charge_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	row.revenue_amount = (row.qty || 0) * (row.sell_rate || 0);
	row.cost_amount = (row.qty || 0) * (row.buy_rate || 0);
	frm.refresh_field('forwarding_charges');
	calculate_forwarding_totals(frm);
}

function calculate_forwarding_totals(frm) {
	let total_revenue = 0;
	let total_cost = 0;

	(frm.doc.forwarding_charges || []).forEach(row => {
		total_revenue += row.revenue_amount || 0;
		total_cost += row.cost_amount || 0;
	});

	const profit = total_revenue - total_cost;
	const rate = frm.doc.conversion_rate || 1.0;

	set_main_value_safe(frm, 'total_estimated_revenue', total_revenue);
	set_main_value_safe(frm, 'total_estimated_cost', total_cost);
	set_main_value_safe(frm, 'total_estimated_profit', profit);

	set_main_value_safe(frm, 'total_estimated_revenue_base', total_revenue * rate);
	set_main_value_safe(frm, 'total_estimated_cost_base', total_cost * rate);
	set_main_value_safe(frm, 'total_estimated_profit_base', profit * rate);
}

// Show/hide base currency fields
function toggle_base_fields(frm) {
    const hide = frm.doc.currency === frm.doc.base_currency;
    
    // Costing base fields
    frm.toggle_display("total_estimated_revenue_base", !hide);
    frm.toggle_display("total_estimated_cost_base", !hide);
    frm.toggle_display("total_estimated_profit_base", !hide);
    
    // Actuals base fields
    frm.toggle_display("total_txn_revenue_base", !hide);
    frm.toggle_display("total_txn_base", !hide);  // cost base
    frm.toggle_display("total_txn_profit_base", !hide);
}

// Update currency labels - UPDATED for both costing and actuals
function update_currency_labels(frm) {
    const currency = frm.doc.currency || "USD";
    const base_currency = frm.doc.base_currency || "USD";

    // Costing labels
    const costing_labels = {
        total_estimated_revenue: `Total Estimated Revenue (${currency})`,
        total_estimated_cost: `Total Estimated Cost (${currency})`,
        total_estimated_profit: `Total Estimated Profit (${currency})`,
        total_estimated_revenue_base: `Total Estimated Revenue (${base_currency})`,
        total_estimated_cost_base: `Total Estimated Cost (${base_currency})`,
        total_estimated_profit_base: `Total Estimated Profit (${base_currency})`
    };

    // Actuals labels
    const actuals_labels = {
        total_txn_revenue: `Total Revenue (${currency})`,
        total_txn_cost: `Total Cost (${currency})`,
        total_txn_profit: `Total Profit (${currency})`,
        total_txn_revenue_base: `Total Revenue (${base_currency})`,
        total_txn_base: `Total Cost (${base_currency})`,  // Note: field is total_txn_base
        total_txn_profit_base: `Total Profit (${base_currency})`
    };

    // Apply costing labels
    for (const [field, label] of Object.entries(costing_labels)) {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "label", label);
        }
    }

    // Apply actuals labels
    for (const [field, label] of Object.entries(actuals_labels)) {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "label", label);
        }
    }

    // Update costing child table labels
    if (frm.fields_dict.forwarding_costing_charges) {
        const grid = frm.fields_dict.forwarding_costing_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }
    
    // Update revenue charges child table labels
    if (frm.fields_dict.forwarding_revenue_charges) {
        const grid = frm.fields_dict.forwarding_revenue_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    }
    
    // Update cost charges child table labels
    if (frm.fields_dict.forwarding_cost_charges) {
        const grid = frm.fields_dict.forwarding_cost_charges.grid;
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }
}

// ==========================================================
// Charge Row Field Locking and Deletion Prevention
// ==========================================================

frappe.ui.form.on('Forwarding Charges', {
	forwarding_charges_add(frm, cdt, cdn) {
		// Default customer from parent customer field
		frappe.model.set_value(cdt, cdn, 'customer', frm.doc.customer);
	},
	
	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const grid_row = frm.fields_dict.forwarding_charges.grid.grid_rows_by_docname[cdn];

		if (row.sales_invoice_reference) {
			grid_row.columns.forEach(col => {
				if (col.df.fieldname !== 'sales_invoice_reference') {
					col.df.read_only = 1;
				}
			});
		}

		if (row.purchase_invoice_reference) {
			grid_row.columns.forEach(col => {
				if (col.df.fieldname !== 'purchase_invoice_reference') {
					col.df.read_only = 1;
				}
			});
		}

		grid_row.refresh();
	},

	before_forwarding_charges_remove(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.sales_invoice_reference || row.purchase_invoice_reference) {
			frappe.throw(__("Cannot delete row that has been invoiced. Please remove the invoice reference first."));
		}
	},

	qty: update_charge_row,
	sell_rate: update_charge_row,
	buy_rate: update_charge_row,
	forwarding_charges_remove(frm) {
		calculate_forwarding_totals(frm);
	}
});

// ==========================================================
// Safe Value Setter
// Only set value if changed to avoid dirty states
// ==========================================================

function set_main_value_safe(frm, fieldname, value) {
	const field = frm.fields_dict[fieldname];
	if (!field || field.df.fieldtype === "Date" || field.df.fieldtype === "Datetime" || frm.doc[fieldname] !== value) {
		frm.set_value(fieldname, value);
	}
}

// ==========================================================
// Cargo Count Summary Logic (Containerised + Packages)
// ==========================================================

function update_cargo_count_forwarding(frm) {
	const table = frm.doc.cargo_parcel_details || [];
	let container_counts = {};
	let package_count = 0;

	table.forEach(row => {
		if (row.cargo_type?.toLowerCase() === "containerised") {
			let ctype = row.container_type || "Unknown Type";
			container_counts[ctype] = (container_counts[ctype] || 0) + 1;
		} else {
			package_count += row.cargo_quantity || 1;
		}
	});

	let summary = [];
	for (const type in container_counts) {
		summary.push(`${container_counts[type]} x ${type}`);
	}
	if (package_count > 0) {
		summary.push(`${package_count} x PKG${package_count > 1 ? "s" : ""}`);
	}

	set_main_value_safe(frm, "cargo_count", summary.join(", "));
}

// ==========================================================
// Cargo Parcel Details Table Triggers
// ==========================================================

frappe.ui.form.on('Cargo Parcel Details', {
	cargo_parcel_details_add(frm, cdt, cdn) {
		// Default cargo item description from parent cargo description
		frappe.model.set_value(cdt, cdn, 'cargo_item_description', frm.doc.cargo_description);
	},
	cargo_type: update_cargo_count_forwarding,
	container_type: update_cargo_count_forwarding,
	cargo_quantity: update_cargo_count_forwarding,
	cargo_parcel_details_remove: update_cargo_count_forwarding
});

// ==========================================================
// Invoicing Dialog Logic
// ==========================================================

function create_sales_invoice_from_charges(frm) {
    // Use forwarding_revenue_charges instead of forwarding_charges
    const all_rows = frm.doc.forwarding_revenue_charges || [];
    const eligible_rows = all_rows.filter(row => 
        row.sell_rate && row.customer && !row.sales_invoice_reference
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible revenue charges found for invoicing."));
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
                <select id="customer-filter" class="form-control" style="width: 100%;">
                    <option value="">-- All Customers --</option>
                    ${customers.map(c =>
                        `<option value="${c}" ${c === customer ? 'selected' : ''}>${c}</option>`
                    ).join('')}
                </select>
            </div>
        `;

        const table = `
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead style="background-color: #f8f9fa; position: sticky; top: 0; z-index: 10;">
                        <tr>
                            <th style="width: 40px; text-align: center;">
                                <input type="checkbox" id="select-all-charges" title="Select All">
                            </th>
                            <th style="min-width: 150px;">Customer</th>
                            <th style="min-width: 200px;">Description</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Sell Rate</th>
                            <th style="width: 100px; text-align: right;">Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
                                </td>
                                <td>${row.customer || ''}</td>
                                <td>${row.charge || ''}</td>
                                <td style="text-align: right;">${row.qty || 0}</td>
                                <td style="text-align: right;">${frappe.format(row.sell_rate || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                                <td style="text-align: right;">${frappe.format(row.revenue_amount || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            ${rows.length === 0 ? '<p style="text-align: center; color: #999; margin-top: 20px;">No charges available for the selected customer.</p>' : ''}
        `;

        dialog.fields_dict.charge_rows_html.$wrapper.html(customer_filter + table);

        // Customer filter change handler
        dialog.$wrapper.find('#customer-filter').on('change', function() {
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
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one charge."));
                return;
            }

            const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
            const unique_customers = [...new Set(selected_rows.map(r => r.customer))];

            if (unique_customers.length > 1) {
                frappe.msgprint(__("You can only create an invoice for one customer at a time."));
                return;
            }

            frappe.call({
                method: "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_sales_invoice_with_rows",
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

function create_purchase_invoice_from_charges(frm) {
    // Use forwarding_cost_charges instead of forwarding_charges
    const all_rows = frm.doc.forwarding_cost_charges || [];
    const eligible_rows = all_rows.filter(row => 
        row.buy_rate && row.supplier && !row.purchase_invoice_reference
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible cost charges found for purchase invoicing."));
        return;
    }

    let selected_supplier = eligible_rows[0].supplier;

    const get_unique_suppliers = () => [...new Set(eligible_rows.map(r => r.supplier))];

    const render_dialog_ui = (dialog, supplier) => {
        const suppliers = get_unique_suppliers();
        const rows = supplier ? eligible_rows.filter(r => r.supplier === supplier) : eligible_rows;

        const supplier_filter = `
            <div style="margin-bottom: 15px;">
                <label for="supplier-filter" style="font-weight: bold; margin-bottom: 5px; display: block;">Supplier:</label>
                <select id="supplier-filter" class="form-control" style="width: 100%;">
                    <option value="">-- All Suppliers --</option>
                    ${suppliers.map(s =>
                        `<option value="${s}" ${s === supplier ? 'selected' : ''}>${s}</option>`
                    ).join('')}
                </select>
            </div>
        `;

        const table = `
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead style="background-color: #f8f9fa; position: sticky; top: 0; z-index: 10;">
                        <tr>
                            <th style="width: 40px; text-align: center;">
                                <input type="checkbox" id="select-all-charges" title="Select All">
                            </th>
                            <th style="min-width: 150px;">Supplier</th>
                            <th style="min-width: 200px;">Charge</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Buy Rate</th>
                            <th style="width: 100px; text-align: right;">Cost</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
                                </td>
                                <td>${row.supplier || ''}</td>
                                <td>${row.charge || ''}</td>
                                <td style="text-align: right;">${row.qty || 0}</td>
                                <td style="text-align: right;">${frappe.format(row.buy_rate || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                                <td style="text-align: right;">${frappe.format(row.cost_amount || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            ${rows.length === 0 ? '<p style="text-align: center; color: #999; margin-top: 20px;">No charges available for the selected supplier.</p>' : ''}
        `;

        dialog.fields_dict.charge_rows_html.$wrapper.html(supplier_filter + table);

        // Supplier filter change handler
        dialog.$wrapper.find('#supplier-filter').on('change', function() {
            selected_supplier = this.value;
            render_dialog_ui(dialog, selected_supplier);
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
        title: __('Select Charges for Purchase Invoice'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'charge_rows_html',
                options: ''
            }
        ],
        primary_action_label: __('Create Purchase Invoice'),
        primary_action() {
            const selected = Array.from(
                dialog.$wrapper.find('.charge-row-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one charge."));
                return;
            }

            const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
            const unique_suppliers = [...new Set(selected_rows.map(r => r.supplier))];

            if (unique_suppliers.length > 1) {
                frappe.msgprint(__("You can only create an invoice for one supplier at a time."));
                return;
            }

            frappe.call({
                method: "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_purchase_invoice_with_rows",
                args: {
                    docname: frm.doc.name,
                    row_names: selected
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Purchase Invoice Created'),
                            message: __('Purchase Invoice {0} has been created successfully', [r.message]),
                            indicator: 'green'
                        });
                        
                        frappe.set_route("Form", "Purchase Invoice", r.message);
                        frm.reload_doc();
                        dialog.hide();
                    }
                }
            });
        }
    });

    dialog.show();
    render_dialog_ui(dialog, selected_supplier);
}

// ==========================================================
// Fetch Charges from Quotation - UPDATED for Costing Table
// ==========================================================

function open_fetch_charges_from_quotation_dialog(frm) {
    if (!frm.doc.customer) {
        frappe.msgprint(__('Please select a Customer first.'));
        return;
    }
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Quotation',
            filters: [
                ['docstatus', '=', 1],
                ['job_type', '=', "Forwarding"],
                ['customer_name', '=', frm.doc.customer],
                ['valid_till', '>=', frappe.datetime.nowdate()]
            ],
            fields: ['name', 'customer_name', 'origin_port', 'destination_port', 'valid_till'],
            limit_page_length: 50,
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                let quotation_options = r.message.map(q =>
                    `${q.name} (${q.customer_name || ''} / ${q.origin_port || ''} → ${q.destination_port || ''})`
                );
                let quotation_names = r.message.map(q => q.name);

                let d = new frappe.ui.Dialog({
                    title: __('Fetch Charges from Quotation'),
                    fields: [
                        {
                            fieldname: 'quotation',
                            label: 'Quotation',
                            fieldtype: 'Select',
                            options: quotation_options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Fetch Charges',
                    primary_action(values) {
                        let idx = quotation_options.indexOf(values.quotation);
                        if (idx >= 0) {
                            let quotation_name = quotation_names[idx];
                            fetch_and_append_quotation_charges(frm, quotation_name);
                        }
                        d.hide();
                    }
                });
                d.show();
            } else {
                frappe.msgprint(__('No valid Forwarding Quotations found for this customer.'));
            }
        }
    });
}

function fetch_and_append_quotation_charges(frm, quotation_name) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Quotation',
            name: quotation_name
        },
        callback: function (r) {
            if (r.message && r.message.items) {
                let items = r.message.items;
                let parent_customer = r.message.customer_name;
                
                // Check existing charges in COSTING table (not forwarding_charges)
                let existing_charges = (frm.doc.forwarding_costing_charges || []).map(row => row.charge);

                let added_count = 0;
                items.forEach(item => {
                    if (!existing_charges.includes(item.item_code)) {
                        // Add to forwarding_costing_charges table
                        let child = frm.add_child('forwarding_costing_charges', {
                            charge: item.item_code,
                            description: strip_html_tags(item.description),
                            qty: item.qty,
                            sell_rate: item.rate,
                            buy_rate: item.buy_rate,
                            supplier: item.supplier,
                            customer: parent_customer
                        });
                        
                        // Calculate amounts (will be recalculated by triggers, but set initial values)
                        child.revenue_amount = (item.qty || 0) * (item.rate || 0);
                        child.cost_amount = (item.qty || 0) * (item.buy_rate || 0);
                        child.margin_amount = child.revenue_amount - child.cost_amount;
                        
                        if (child.revenue_amount > 0) {
                            child.margin_percentage = (child.margin_amount / child.revenue_amount) * 100;
                        } else {
                            child.margin_percentage = 0;
                        }
                        
                        added_count += 1;
                    }
                });

                // Refresh the costing charges table
                frm.refresh_field('forwarding_costing_charges');
                
                // Recalculate costing totals
                calculate_costing_totals(frm);

                if (added_count === 0) {
                    frappe.msgprint(__('All quotation charges already exist in the costing table. No new charges added.'));
                } else {
                    frappe.msgprint(__(`${added_count} charge(s) loaded from quotation into Job Costing table.`));
                }
            }
        }
    });
}

// Strip HTML tags from a description string
function strip_html_tags(html) {
    let tmp = document.createElement("DIV");
    tmp.innerHTML = html || "";
    return tmp.textContent || tmp.innerText || "";
}

// ===================================
// FORWARDING COSTING CHARGES
// ===================================
frappe.ui.form.on('Forwarding Costing Charges', {
    forwarding_costing_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_costing_totals(frm);
    },
    
    forwarding_costing_charges_remove: function(frm) {
        calculate_costing_totals(frm);
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_costing_charge_amounts(frm, cdt, cdn);
    },
    
    sell_rate: function(frm, cdt, cdn) {
        calculate_costing_charge_amounts(frm, cdt, cdn);
    },
    
    buy_rate: function(frm, cdt, cdn) {
        calculate_costing_charge_amounts(frm, cdt, cdn);
    }
});

// ===================================
// FORWARDING REVENUE CHARGES
// ===================================
frappe.ui.form.on('Forwarding Revenue Charges', {
    forwarding_revenue_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_actual_totals(frm);
    },
    
    forwarding_revenue_charges_remove: function(frm) {
        calculate_actual_totals(frm);
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_revenue_charge_amounts(frm, cdt, cdn);
    },
    
    sell_rate: function(frm, cdt, cdn) {
        calculate_revenue_charge_amounts(frm, cdt, cdn);
    }
});

// ===================================
// FORWARDING COST CHARGES
// ===================================
frappe.ui.form.on('Forwarding Cost Charges', {
    forwarding_cost_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_actual_totals(frm);
    },
    
    forwarding_cost_charges_remove: function(frm) {
        calculate_actual_totals(frm);
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_cost_charge_amounts(frm, cdt, cdn);
    },
    
    buy_rate: function(frm, cdt, cdn) {
        calculate_cost_charge_amounts(frm, cdt, cdn);
    }
});

// ===================================
// CALCULATION FUNCTIONS
// ===================================

// Helper function: Calculate individual costing line amounts
function calculate_costing_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Get quantity (default to 1)
    let qty = flt(row.qty) || 1;
    
    // Calculate revenue amount (sell side)
    let sell_rate = flt(row.sell_rate) || 0;
    let revenue_amount = qty * sell_rate;
    
    // Calculate cost amount (buy side)
    let buy_rate = flt(row.buy_rate) || 0;
    let cost_amount = qty * buy_rate;
    
    // Calculate margin
    let margin_amount = revenue_amount - cost_amount;
    let margin_percentage = revenue_amount > 0 ? (margin_amount / revenue_amount * 100) : 0;
    
    // Update row values
    frappe.model.set_value(cdt, cdn, 'revenue_amount', revenue_amount);
    frappe.model.set_value(cdt, cdn, 'cost_amount', cost_amount);
    frappe.model.set_value(cdt, cdn, 'margin_amount', margin_amount);
    frappe.model.set_value(cdt, cdn, 'margin_percentage', margin_percentage);
    
    // Recalculate totals
    calculate_costing_totals(frm);
}

function calculate_costing_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;
    
    // Sum all costing charges
    $.each(frm.doc.forwarding_costing_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
        total_cost += flt(row.cost_amount);
    });
    
    let total_profit = total_revenue - total_cost;
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? (total_profit / total_revenue * 100) : 0;
    
    // Update totals in transaction currency
    set_main_value_safe(frm, 'total_estimated_revenue', total_revenue);
    set_main_value_safe(frm, 'total_estimated_cost', total_cost);
    set_main_value_safe(frm, 'total_estimated_profit', total_profit);
    set_main_value_safe(frm, 'estimated_profit_margin_percent', profit_margin_percent);
    
    // Update totals in base currency
    set_main_value_safe(frm, 'total_estimated_revenue_base', total_revenue * rate);
    set_main_value_safe(frm, 'total_estimated_cost_base', total_cost * rate);
    set_main_value_safe(frm, 'total_estimated_profit_base', total_profit * rate);
    
    frm.refresh_fields();
}

function calculate_revenue_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Get quantity (default to 1)
    let qty = flt(row.qty) || 1;
    
    // Calculate revenue amount
    let sell_rate = flt(row.sell_rate) || 0;
    let revenue_amount = qty * sell_rate;
    
    // Update revenue amount
    frappe.model.set_value(cdt, cdn, 'revenue_amount', revenue_amount);
    
    // Recalculate totals
    calculate_actual_totals(frm);
}

function calculate_cost_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Get quantity (default to 1)
    let qty = flt(row.qty) || 1;
    
    // Calculate cost amount
    let buy_rate = flt(row.buy_rate) || 0;
    let cost_amount = qty * buy_rate;
    
    // Update cost amount
    frappe.model.set_value(cdt, cdn, 'cost_amount', cost_amount);
    
    // Recalculate totals
    calculate_actual_totals(frm);
}

function calculate_actual_totals(frm) {
    // Initialize totals
    let total_revenue = 0;
    let total_cost = 0;
    
    // Sum all actual revenue charges
    $.each(frm.doc.forwarding_revenue_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
    });
    
    // Sum all actual cost charges
    $.each(frm.doc.forwarding_cost_charges || [], function(i, row) {
        total_cost += flt(row.cost_amount);
    });
    
    // Calculate profit
    let total_profit = total_revenue - total_cost;
    
    // Get conversion rate (same as costing)
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    
    // Calculate profit margin percentage - EXACTLY like costing
    let profit_margin_percent = total_revenue > 0 ? (total_profit / total_revenue * 100) : 0;
    
    // Update actual totals in transaction currency
    set_main_value_safe(frm, 'total_txn_revenue', total_revenue);
    set_main_value_safe(frm, 'total_txn_cost', total_cost);
    set_main_value_safe(frm, 'total_txn_profit', total_profit);
    set_main_value_safe(frm, 'profit_margin_percent', profit_margin_percent);
    
    // Update actual totals in base currency
    set_main_value_safe(frm, 'total_txn_revenue_base', total_revenue * rate);
    set_main_value_safe(frm, 'total_txn_base', total_cost * rate);
    set_main_value_safe(frm, 'total_txn_profit_base', total_profit * rate);
    
    frm.refresh_fields();
}

// Show/hide base currency fields - FOR BOTH COSTING AND ACTUALS
function toggle_base_fields(frm) {
    const hide = frm.doc.currency === frm.doc.base_currency;
    
    // Costing base fields
    frm.toggle_display("total_estimated_revenue_base", !hide);
    frm.toggle_display("total_estimated_cost_base", !hide);
    frm.toggle_display("total_estimated_profit_base", !hide);
    
    // Actuals base fields
    frm.toggle_display("total_txn_revenue_base", !hide);
    frm.toggle_display("total_txn_base", !hide);
    frm.toggle_display("total_txn_profit_base", !hide);
}

// Update currency labels - FOR BOTH COSTING AND ACTUALS
function update_currency_labels(frm) {
    const currency = frm.doc.currency || "USD";
    const base_currency = frm.doc.base_currency || "USD";

    // Costing labels
    const costing_labels = {
        total_estimated_revenue: `Total Estimated Revenue (${currency})`,
        total_estimated_cost: `Total Estimated Cost (${currency})`,
        total_estimated_profit: `Total Estimated Profit (${currency})`,
        total_estimated_revenue_base: `Total Estimated Revenue (${base_currency})`,
        total_estimated_cost_base: `Total Estimated Cost (${base_currency})`,
        total_estimated_profit_base: `Total Estimated Profit (${base_currency})`
    };

    // Actuals labels
    const actuals_labels = {
        total_txn_revenue: `Total Revenue (${currency})`,
        total_txn_cost: `Total Cost (${currency})`,
        total_txn_profit: `Total Profit (${currency})`,
        total_txn_revenue_base: `Total Revenue (${base_currency})`,
        total_txn_base: `Total Cost (${base_currency})`,
        total_txn_profit_base: `Total Profit (${base_currency})`
    };

    // Apply costing labels
    for (const [field, label] of Object.entries(costing_labels)) {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "label", label);
        }
    }

    // Apply actuals labels
    for (const [field, label] of Object.entries(actuals_labels)) {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "label", label);
        }
    }

    // Update costing child table labels
    if (frm.fields_dict.forwarding_costing_charges) {
        const grid = frm.fields_dict.forwarding_costing_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }
    
    // Update revenue charges child table labels
    if (frm.fields_dict.forwarding_revenue_charges) {
        const grid = frm.fields_dict.forwarding_revenue_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    }
    
    // Update cost charges child table labels
    if (frm.fields_dict.forwarding_cost_charges) {
        const grid = frm.fields_dict.forwarding_cost_charges.grid;
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }
}

// Safe Value Setter (from original code)
function set_main_value_safe(frm, fieldname, value) {
    const field = frm.fields_dict[fieldname];
    if (!field || field.df.fieldtype === "Date" || field.df.fieldtype === "Datetime" || frm.doc[fieldname] !== value) {
        frm.set_value(fieldname, value);
    }
}

// ==========================================================
// Invoicing Dialog Logic
// ==========================================================

function create_sales_invoice_from_charges(frm) {
    // Use forwarding_revenue_charges instead of forwarding_charges
    const all_rows = frm.doc.forwarding_revenue_charges || [];
    const eligible_rows = all_rows.filter(row => 
        row.sell_rate && row.customer && !row.sales_invoice_reference
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible revenue charges found for invoicing."));
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
                <select id="customer-filter" class="form-control" style="width: 100%;">
                    <option value="">-- All Customers --</option>
                    ${customers.map(c =>
                        `<option value="${c}" ${c === customer ? 'selected' : ''}>${c}</option>`
                    ).join('')}
                </select>
            </div>
        `;

        const table = `
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead style="background-color: #f8f9fa; position: sticky; top: 0; z-index: 10;">
                        <tr>
                            <th style="width: 40px; text-align: center;">
                                <input type="checkbox" id="select-all-charges" title="Select All">
                            </th>
                            <th style="min-width: 150px;">Customer</th>
                            <th style="min-width: 200px;">Description</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Sell Rate</th>
                            <th style="width: 100px; text-align: right;">Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
                                </td>
                                <td>${row.customer || ''}</td>
                                <td>${row.charge || ''}</td>
                                <td style="text-align: right;">${row.qty || 0}</td>
                                <td style="text-align: right;">${frappe.format(row.sell_rate || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                                <td style="text-align: right;">${frappe.format(row.revenue_amount || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            ${rows.length === 0 ? '<p style="text-align: center; color: #999; margin-top: 20px;">No charges available for the selected customer.</p>' : ''}
        `;

        dialog.fields_dict.charge_rows_html.$wrapper.html(customer_filter + table);

        // Customer filter change handler
        dialog.$wrapper.find('#customer-filter').on('change', function() {
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
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one charge."));
                return;
            }

            const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
            const unique_customers = [...new Set(selected_rows.map(r => r.customer))];

            if (unique_customers.length > 1) {
                frappe.msgprint(__("You can only create an invoice for one customer at a time."));
                return;
            }

            frappe.call({
                method: "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_sales_invoice_with_rows",
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

function create_purchase_invoice_from_charges(frm) {
    // Use forwarding_cost_charges instead of forwarding_charges
    const all_rows = frm.doc.forwarding_cost_charges || [];
    const eligible_rows = all_rows.filter(row => 
        row.buy_rate && row.supplier && !row.purchase_invoice_reference
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible cost charges found for purchase invoicing."));
        return;
    }

    let selected_supplier = eligible_rows[0].supplier;

    const get_unique_suppliers = () => [...new Set(eligible_rows.map(r => r.supplier))];

    const render_dialog_ui = (dialog, supplier) => {
        const suppliers = get_unique_suppliers();
        const rows = supplier ? eligible_rows.filter(r => r.supplier === supplier) : eligible_rows;

        const supplier_filter = `
            <div style="margin-bottom: 15px;">
                <label for="supplier-filter" style="font-weight: bold; margin-bottom: 5px; display: block;">Supplier:</label>
                <select id="supplier-filter" class="form-control" style="width: 100%;">
                    <option value="">-- All Suppliers --</option>
                    ${suppliers.map(s =>
                        `<option value="${s}" ${s === supplier ? 'selected' : ''}>${s}</option>`
                    ).join('')}
                </select>
            </div>
        `;

        const table = `
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead style="background-color: #f8f9fa; position: sticky; top: 0; z-index: 10;">
                        <tr>
                            <th style="width: 40px; text-align: center;">
                                <input type="checkbox" id="select-all-charges" title="Select All">
                            </th>
                            <th style="min-width: 150px;">Supplier</th>
                            <th style="min-width: 200px;">Charge</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Buy Rate</th>
                            <th style="width: 100px; text-align: right;">Cost</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
                                </td>
                                <td>${row.supplier || ''}</td>
                                <td>${row.charge || ''}</td>
                                <td style="text-align: right;">${row.qty || 0}</td>
                                <td style="text-align: right;">${frappe.format(row.buy_rate || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                                <td style="text-align: right;">${frappe.format(row.cost_amount || 0, { 
                                    fieldtype: 'Currency', 
                                    currency: frm.doc.currency 
                                })}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            ${rows.length === 0 ? '<p style="text-align: center; color: #999; margin-top: 20px;">No charges available for the selected supplier.</p>' : ''}
        `;

        dialog.fields_dict.charge_rows_html.$wrapper.html(supplier_filter + table);

        // Supplier filter change handler
        dialog.$wrapper.find('#supplier-filter').on('change', function() {
            selected_supplier = this.value;
            render_dialog_ui(dialog, selected_supplier);
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
        title: __('Select Charges for Purchase Invoice'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'charge_rows_html',
                options: ''
            }
        ],
        primary_action_label: __('Create Purchase Invoice'),
        primary_action() {
            const selected = Array.from(
                dialog.$wrapper.find('.charge-row-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one charge."));
                return;
            }

            const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
            const unique_suppliers = [...new Set(selected_rows.map(r => r.supplier))];

            if (unique_suppliers.length > 1) {
                frappe.msgprint(__("You can only create an invoice for one supplier at a time."));
                return;
            }

            frappe.call({
                method: "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_purchase_invoice_with_rows",
                args: {
                    docname: frm.doc.name,
                    row_names: selected
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Purchase Invoice Created'),
                            message: __('Purchase Invoice {0} has been created successfully', [r.message]),
                            indicator: 'green'
                        });
                        
                        frappe.set_route("Form", "Purchase Invoice", r.message);
                        frm.reload_doc();
                        dialog.hide();
                    }
                }
            });
        }
    });

    dialog.show();
    render_dialog_ui(dialog, selected_supplier);
}