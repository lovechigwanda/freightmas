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
        // WEB PORTAL BUTTON (Updated to use is_trucking_required)
        // ========================================
        if (frm.doc.is_trucking_required && !frm.is_new()) {
            // Add simple "Web Portal" button under View menu
            frm.page.add_inner_button(__('Web Portal'), function() {
                const url = `${window.location.origin}/truck_portal?job=${frm.doc.name}`;
                window.open(url, '_blank');
            }, __('View'));
        }
        
        // ========================================
        // UI-only updates on refresh (do NOT write calculated totals to frm.doc here)
        // ========================================
        toggle_base_fields(frm);
        update_currency_labels(frm);
        update_cargo_count_forwarding(frm);

        // ========================================
        // CUSTOM BUTTONS
        // ========================================
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

    fetch_revenue_from_job_costing: function(frm) {
        if (!frm.doc.name) {
            frappe.msgprint(__('Please save the document first.'));
            return;
        }
        
        frappe.call({
            method: 'fetch_revenue_from_costing',
            doc: frm.doc,
            callback: function(r) {
                if (r && r.message !== undefined) {
                    const added = r.message || 0;
                    if (added > 0) {
                        frm.reload_doc();
                    }
                }
            }
        });
    },

    fetch_cost_from_job_costing: function(frm) {
        if (!frm.doc.name) {
            frappe.msgprint(__('Please save the document first.'));
            return;
        }
        
        frappe.call({
            method: 'fetch_cost_from_costing',
            doc: frm.doc,
            callback: function(r) {
                if (r && r.message !== undefined) {
                    const added = r.message || 0;
                    if (added > 0) {
                        frm.reload_doc();
                    }
                }
            }
        });
    },

    fetch_cost_from_truck_loading: function(frm) {
        if (!frm.doc.name) {
            frappe.msgprint(__('Please save the document first.'));
            return;
        }
        
        frappe.call({
            method: 'fetch_cost_from_truck_loading',
            doc: frm.doc,
            callback: function(r) {
                if (r && r.message !== undefined) {
                    const added = r.message || 0;
                    if (added > 0) {
                        frm.reload_doc();
                    }
                }
            }
        });
    }
});

// ==========================================================
// Safe Value Setter
// ==========================================================

function set_main_value_safe(frm, fieldname, value) {
    const current = frm.doc[fieldname];

    // Normalize both values to a canonical string form so numbers/strings/objects
    // compare consistently and identical values don't trigger a set_value call.
    const normalize = v => {
        if (v === undefined || v === null) return "";
        if (typeof v === "number") {
            // Use plain string form for numbers
            return v.toString();
        }
        if (typeof v === "boolean") {
            return v ? "1" : "0";
        }
        if (v instanceof Date) {
            return v.toISOString();
        }
        if (typeof v === "object") {
            try {
                // Stable representation for objects/arrays
                return JSON.stringify(v);
            } catch (e) {
                return String(v);
            }
        }
        return String(v);
    };

    if (normalize(current) === normalize(value)) {
        return;
    }

    // Only set when values differ
    frm.set_value(fieldname, value);
}

// ==========================================================
// Show/Hide Base Currency Fields
// ==========================================================

function toggle_base_fields(frm) {
    const show = frm.doc.currency !== frm.doc.base_currency;
    
    // Costing section
    frm.toggle_display('total_estimated_revenue_base', show);
    frm.toggle_display('total_estimated_cost_base', show);
    frm.toggle_display('total_estimated_profit_base', show);
    
    // Actuals section
    frm.toggle_display('total_txn_revenue_base', show);
    frm.toggle_display('total_txn_base', show);
    frm.toggle_display('total_txn_profit_base', show);
}

// ==========================================================
// Update Currency Labels
// ==========================================================

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

// ==========================================================
// Cargo Count Summary
// ==========================================================

function update_cargo_count_forwarding(frm) {
    const cargo_details = frm.doc.cargo_parcel_details || [];
    const containerised = cargo_details.filter(c => c.cargo_type === "Containerised");
    const packages = cargo_details.filter(c => c.cargo_type === "Packages");

    let summary_parts = [];

    if (containerised.length > 0) {
        const grouped = {};
        containerised.forEach(c => {
            const key = c.container_type || "Unknown";
            grouped[key] = (grouped[key] || 0) + (c.cargo_quantity || 0);
        });
        const containerPart = Object.entries(grouped)
            .map(([type, qty]) => `${qty}x${type}`)
            .join(", ");
        summary_parts.push(containerPart);
    }

    if (packages.length > 0) {
        const total_packages = packages.reduce((sum, p) => sum + (p.cargo_quantity || 0), 0);
        summary_parts.push(`${total_packages} Packages`);
    }

    const summary = summary_parts.length > 0 ? summary_parts.join(" + ") : "";
    set_main_value_safe(frm, 'cargo_count', summary);
}

frappe.ui.form.on('Cargo Parcel Details', {
    cargo_parcel_details_add(frm, cdt, cdn) {
        update_cargo_count_forwarding(frm);
    },
    cargo_type: update_cargo_count_forwarding,
    container_type: update_cargo_count_forwarding,
    cargo_quantity: update_cargo_count_forwarding,
    cargo_parcel_details_remove: update_cargo_count_forwarding
});

// ==========================================================
// Invoicing Dialog Functions
// ==========================================================

function create_sales_invoice_from_charges(frm) {
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
        // ensure a stable unique token for scoping if needed
        const customers = get_unique_customers();
        const rows = customer ? eligible_rows.filter(r => r.customer === customer) : eligible_rows;

        const customer_filter = `
            <div style="margin-bottom: 15px;">
                <label for="" style="font-weight: bold; margin-bottom: 5px; display: block;">Customer:</label>
                <select class="customer-filter form-control" style="width: 100%;">
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
                                <input type="checkbox" class="select-all-charges" title="Select All">
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
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name || ''}" ${!row.name ? 'disabled title="Save the Job to invoice this newly added row"' : ''}>
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

        // unbind then rebind handlers to avoid duplicates
        dialog.$wrapper.find('.customer-filter').off('change').on('change', function() {
            selected_customer = this.value;
            render_dialog_ui(dialog, selected_customer);
        });

        dialog.$wrapper.find('.select-all-charges').off('change').on('change', function() {
            const isChecked = this.checked;
            dialog.$wrapper.find('.charge-row-check').prop('checked', isChecked);
        });

        dialog.$wrapper.find('.charge-row-check').off('change').on('change', function() {
            const total = dialog.$wrapper.find('.charge-row-check').length;
            const checked = dialog.$wrapper.find('.charge-row-check:checked').length;
            dialog.$wrapper.find('.select-all-charges').prop('checked', total === checked);
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
            const checked = dialog.$wrapper.find('.charge-row-check:checked');
            const selected_rows = [];
            checked.each(function() {
                const rn = $(this).data('row-name');
                if (rn) selected_rows.push(rn);
            });

            if (!selected_rows.length) {
                frappe.msgprint(__('Please select at least one charge.'));
                return;
            }

            frappe.call({
                method: 'freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_sales_invoice_with_rows',
                args: {
                    docname: frm.doc.name,
                    row_names: selected_rows
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
                <label for="" style="font-weight: bold; margin-bottom: 5px; display: block;">Supplier:</label>
                <select class="supplier-filter form-control" style="width: 100%;">
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
                                <input type="checkbox" class="select-all-charges" title="Select All">
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
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name || ''}" ${!row.name ? 'disabled title="Save the Job to invoice this newly added row"' : ''}>
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

        dialog.$wrapper.find('.supplier-filter').off('change').on('change', function() {
            selected_supplier = this.value;
            render_dialog_ui(dialog, selected_supplier);
        });

        dialog.$wrapper.find('.select-all-charges').off('change').on('change', function() {
            const isChecked = this.checked;
            dialog.$wrapper.find('.charge-row-check').prop('checked', isChecked);
        });

        dialog.$wrapper.find('.charge-row-check').off('change').on('change', function() {
            const total = dialog.$wrapper.find('.charge-row-check').length;
            const checked = dialog.$wrapper.find('.charge-row-check:checked').length;
            dialog.$wrapper.find('.select-all-charges').prop('checked', total === checked);
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
            const checked = dialog.$wrapper.find('.charge-row-check:checked');
            const selected_rows = [];
            checked.each(function() {
                const rn = $(this).data('row-name');
                if (rn) selected_rows.push(rn);
            });

            if (!selected_rows.length) {
                frappe.msgprint(__('Please select at least one charge.'));
                return;
            }

            frappe.call({
                method: 'freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_purchase_invoice_with_rows',
                args: {
                    docname: frm.doc.name,
                    row_names: selected_rows
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
// Fetch Charges from Quotation
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
                    title: __('Select a Quotation'),
                    fields: [
                        {
                            label: __('Quotation'),
                            fieldname: 'quotation',
                            fieldtype: 'Select',
                            options: quotation_options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Fetch Charges'),
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
                frappe.msgprint(__('No valid submitted Forwarding quotations found for this customer.'));
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
                
                let existing_charges = (frm.doc.forwarding_costing_charges || []).map(row => row.charge);

                let added_count = 0;
                items.forEach(item => {
                    if (!existing_charges.includes(item.item_code)) {
                        let child = frm.add_child('forwarding_costing_charges', {
                            charge: item.item_code,
                            description: strip_html_tags(item.description),
                            qty: item.qty,
                            sell_rate: item.rate,
                            buy_rate: item.buy_rate,
                            supplier: item.supplier,
                            customer: parent_customer
                        });
                        
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

                frm.refresh_field('forwarding_costing_charges');
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
    },
    
    form_render(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const grid_row = frm.fields_dict.forwarding_revenue_charges.grid.grid_rows_by_docname[cdn];
        if (row?.sales_invoice_reference) {
            grid_row.columns.forEach(col => {
                if (col.df.fieldname !== 'sales_invoice_reference') {
                    col.df.read_only = 1;
                }
            });
            grid_row.refresh();
        }
    },
    
    before_forwarding_revenue_charges_remove(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row?.sales_invoice_reference) {
            frappe.throw(__('Cannot delete a revenue charge linked to Sales Invoice {0}.', [row.sales_invoice_reference]));
        }
    },
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
    },
    
    form_render(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const grid_row = frm.fields_dict.forwarding_cost_charges.grid.grid_rows_by_docname[cdn];
        if (row?.purchase_invoice_reference) {
            grid_row.columns.forEach(col => {
                if (col.df.fieldname !== 'purchase_invoice_reference') {
                    col.df.read_only = 1;
                }
            });
            grid_row.refresh();
        }
    },
    
    before_forwarding_cost_charges_remove(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row?.purchase_invoice_reference) {
            frappe.throw(__('Cannot delete a cost charge linked to Purchase Invoice {0}.', [row.purchase_invoice_reference]));
        }
    },
});

// ===================================
// CALCULATION FUNCTIONS
// ===================================

function calculate_costing_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let qty = flt(row.qty) || 1;
    let sell_rate = flt(row.sell_rate) || 0;
    let buy_rate = flt(row.buy_rate) || 0;
    
    let revenue_amount = qty * sell_rate;
    let cost_amount = qty * buy_rate;
    let margin_amount = revenue_amount - cost_amount;
    let margin_percentage = revenue_amount > 0 ? (margin_amount / revenue_amount * 100) : 0;
    
    frappe.model.set_value(cdt, cdn, 'revenue_amount', revenue_amount);
    frappe.model.set_value(cdt, cdn, 'cost_amount', cost_amount);
    frappe.model.set_value(cdt, cdn, 'margin_amount', margin_amount);
    frappe.model.set_value(cdt, cdn, 'margin_percentage', margin_percentage);
    
    calculate_costing_totals(frm);
}

function calculate_costing_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;
    
    $.each(frm.doc.forwarding_costing_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
        total_cost += flt(row.cost_amount);
    });
    
    let total_profit = total_revenue - total_cost;
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? (total_profit / total_revenue * 100) : 0;
    
    set_main_value_safe(frm, 'total_estimated_revenue', total_revenue);
    set_main_value_safe(frm, 'total_estimated_cost', total_cost);
    set_main_value_safe(frm, 'total_estimated_profit', total_profit);
    set_main_value_safe(frm, 'estimated_profit_margin_percent', profit_margin_percent);
    
    set_main_value_safe(frm, 'total_estimated_revenue_base', total_revenue * rate);
    set_main_value_safe(frm, 'total_estimated_cost_base', total_cost * rate);
    set_main_value_safe(frm, 'total_estimated_profit_base', total_profit * rate);
    
    frm.refresh_fields();
}

function calculate_revenue_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let qty = flt(row.qty) || 1;
    let sell_rate = flt(row.sell_rate) || 0;
    let revenue_amount = qty * sell_rate;
    
    frappe.model.set_value(cdt, cdn, 'revenue_amount', revenue_amount);
    calculate_actual_totals(frm);
}

function calculate_cost_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let qty = flt(row.qty) || 1;
    let buy_rate = flt(row.buy_rate) || 0;
    let cost_amount = qty * buy_rate;
    
    frappe.model.set_value(cdt, cdn, 'cost_amount', cost_amount);
    calculate_actual_totals(frm);
}

function calculate_actual_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;
    
    $.each(frm.doc.forwarding_revenue_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
    });
    
    $.each(frm.doc.forwarding_cost_charges || [], function(i, row) {
        total_cost += flt(row.cost_amount);
    });
    
    let total_profit = total_revenue - total_cost;
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? (total_profit / total_revenue * 100) : 0;
    
    set_main_value_safe(frm, 'total_txn_revenue', total_revenue);
    set_main_value_safe(frm, 'total_txn_cost', total_cost);
    set_main_value_safe(frm, 'total_txn_profit', total_profit);
    set_main_value_safe(frm, 'profit_margin_percent', profit_margin_percent);
    
    set_main_value_safe(frm, 'total_txn_revenue_base', total_revenue * rate);
    set_main_value_safe(frm, 'total_txn_base', total_cost * rate);
    set_main_value_safe(frm, 'total_txn_profit_base', total_profit * rate);
    
    frm.refresh_fields();
}


//////////////////////////////////////////
/// Prevent editing of costing charges once job is not Draft
//////////////////////////////////////////

// === Forwarding Job: simple client-side lock for Forwarding Costing ===
frappe.ui.form.on('Forwarding Job', {
    refresh(frm) {
        toggle_costing_table_lock(frm);
    },
    status(frm) {
        // re-check when status changes
        toggle_costing_table_lock(frm);
    }
});

function toggle_costing_table_lock(frm) {
    const fieldname = 'forwarding_costing_charges';
    const is_draft = frm.doc.status === 'Draft';

    if (!frm.fields_dict[fieldname]) return;

    // Set DF-level properties which Frappe respects for table actions
    frm.set_df_property(fieldname, 'cannot_add_rows', !is_draft);
    frm.set_df_property(fieldname, 'allow_bulk_edit', is_draft);

    // If grid is not yet rendered, stop here; refresh will run again later
    const grid_field = frm.fields_dict[fieldname];
    const grid = grid_field && grid_field.grid;
    const wrapper = grid_field.$wrapper;

    if (!grid) return;

    // Set read_only on grid df so inputs are default readonly where supported
    grid.df.read_only = !is_draft;

    if (!is_draft) {
        // hide add/duplicate/delete buttons (defensive selectors)
        wrapper.find('.grid-add-row, .grid-duplicate-row, .grid-delete-row, .grid-expand-row').hide();

        // Make existing rendered rows readonly (if possible)
        try {
            if (grid.grid_rows_by_docname) {
                Object.keys(grid.grid_rows_by_docname).forEach(name => {
                    const grid_row = grid.grid_rows_by_docname[name];
                    if (!grid_row || !grid_row.columns) return;
                    grid_row.columns.forEach(col => {
                        if (col && col.df) {
                            col.df.read_only = 1;
                        }
                    });
                    grid_row.refresh();
                });
            } else {
                // Fallback: visually dim and disable pointer events (still copyable if needed)
                wrapper.find('.grid-body').css({'pointer-events': 'none', 'opacity': 0.7});
            }
        } catch (e) {
            console.warn('Error locking costing grid rows', e);
        }

        // Add a one-time lock message (visual)
        if (!wrapper.find('.fm-costing-locked').length) {
            wrapper.find('.grid-heading-row').after(
                `<div class="fm-costing-locked" 
                      style="padding:6px 0 4px 0; margin-top:4px; color:#0b5ed7; font-weight:500; font-size:13px;">
                    Planned Job Costing is locked for editing to maintain budget figures.
                </div>`
            );
        }
    } else {
        // unlock UI
        wrapper.find('.fm-costing-locked').remove();
        wrapper.find('.grid-add-row, .grid-duplicate-row, .grid-delete-row, .grid-expand-row').show();
        wrapper.find('.grid-body').css({'pointer-events': '', 'opacity': ''});

        try {
            if (grid.grid_rows_by_docname) {
                Object.keys(grid.grid_rows_by_docname).forEach(name => {
                    const grid_row = grid.grid_rows_by_docname[name];
                    if (!grid_row || !grid_row.columns) return;
                    grid_row.columns.forEach(col => {
                        if (col && col.df) {
                            col.df.read_only = 0;
                        }
                    });
                    grid_row.refresh();
                });
            }
        } catch (e) {
            console.warn('Error unlocking costing grid rows', e);
        }
    }
}


// ==========================================================
// CARGO MILESTONE VALIDATION
// ==========================================================

frappe.ui.form.on('Cargo Parcel Details', {
    is_truck_required: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_truck_required) {
            // Clear all milestone checkboxes and dates when trucking not required
            clear_all_milestones(row);
            frm.refresh_field('cargo_parcel_details');
        }
    },

    is_booked: function(frm, cdt, cdn) {
        validate_milestone_checkbox(frm, cdt, cdn, 'is_booked', 'booked_on_date');
    },

    is_loaded: function(frm, cdt, cdn) {
        validate_milestone_checkbox(frm, cdt, cdn, 'is_loaded', 'loaded_on_date');
    },

    is_offloaded: function(frm, cdt, cdn) {
        validate_milestone_checkbox(frm, cdt, cdn, 'is_offloaded', 'offloaded_on_date');
    },

    is_returned: function(frm, cdt, cdn) {
        validate_milestone_checkbox(frm, cdt, cdn, 'is_returned', 'returned_on_date');
    },

    is_completed: function(frm, cdt, cdn) {
        validate_milestone_checkbox(frm, cdt, cdn, 'is_completed', 'completed_on_date');
    },

    // Date field validations
    booked_on_date: function(frm, cdt, cdn) {
        validate_milestone_date_sequence(frm, cdt, cdn);
    },

    loaded_on_date: function(frm, cdt, cdn) {
        validate_milestone_date_sequence(frm, cdt, cdn);
    },

    offloaded_on_date: function(frm, cdt, cdn) {
        validate_milestone_date_sequence(frm, cdt, cdn);
    },

    completed_on_date: function(frm, cdt, cdn) {
        validate_milestone_date_sequence(frm, cdt, cdn);
    }
});

function validate_milestone_checkbox(frm, cdt, cdn, checkbox_field, date_field) {
    let row = locals[cdt][cdn];
    
    // Skip validation if trucking not required
    if (!row.is_truck_required) {
        row[checkbox_field] = 0;
        frappe.msgprint(__('Trucking must be required to track milestones'));
        frm.refresh_field('cargo_parcel_details');
        return;
    }

    if (row[checkbox_field]) {
        // Checkbox being ticked - validate progression
        if (!validate_sequential_progression(row, checkbox_field)) {
            row[checkbox_field] = 0;
            frm.refresh_field('cargo_parcel_details');
            return;
        }

        // Validate prerequisites for specific milestones
        if (!validate_milestone_prerequisites(row, checkbox_field)) {
            row[checkbox_field] = 0;
            frm.refresh_field('cargo_parcel_details');
            return;
        }

        // Auto-set date to current if empty - use consistent format
        if (!row[date_field]) {
            row[date_field] = frappe.datetime.get_today(); // This returns YYYY-MM-DD format
        }
    } else {
        // Checkbox being unticked - validate reverse sequence
        if (!validate_reverse_unticking(row, checkbox_field)) {
            row[checkbox_field] = 1;
            frm.refresh_field('cargo_parcel_details');
            return;
        }

        // Clear the corresponding date
        row[date_field] = null;
    }

    frm.refresh_field('cargo_parcel_details');
}

function validate_sequential_progression(row, checkbox_field) {
    const MILESTONE_ORDER = ['is_booked', 'is_loaded', 'is_offloaded', 'is_completed'];
    const current_index = MILESTONE_ORDER.indexOf(checkbox_field);
    
    if (current_index === -1) {
        // Handle is_returned separately (optional)
        if (checkbox_field === 'is_returned') {
            if (!row.to_be_returned) {
                frappe.msgprint(__('Container return is not required for this cargo'));
                return false;
            }
            if (!row.is_offloaded) {
                frappe.msgprint(__('Container must be offloaded before marking as returned'));
                return false;
            }
            return true;
        }
        return true;
    }

    // Check if previous milestones are completed
    for (let i = 0; i < current_index; i++) {
        if (!row[MILESTONE_ORDER[i]]) {
            frappe.msgprint(__(`Please complete ${MILESTONE_ORDER[i].replace('is_', '').replace('_', ' ')} milestone first`));
            return false;
        }
    }

    return true;
}

function validate_reverse_unticking(row, checkbox_field) {
    const MILESTONE_ORDER = ['is_booked', 'is_loaded', 'is_offloaded', 'is_completed'];
    const current_index = MILESTONE_ORDER.indexOf(checkbox_field);
    
    if (current_index === -1) {
        // Handle is_returned separately
        if (checkbox_field === 'is_returned') {
            return true; // Can always untick return
        }
        return true;
    }

    // Check if later milestones are still ticked
    for (let i = current_index + 1; i < MILESTONE_ORDER.length; i++) {
        if (row[MILESTONE_ORDER[i]]) {
            frappe.msgprint(__(`Please untick ${MILESTONE_ORDER[i].replace('is_', '').replace('_', ' ')} milestone first`));
            return false;
        }
    }

    // Also check if is_returned is ticked
    if (row.is_returned && current_index <= 2) { // offloaded or earlier
        frappe.msgprint(__('Please untick "Is Returned" milestone first'));
        return false;
    }

    return true;
}

function validate_milestone_prerequisites(row, checkbox_field) {
    switch(checkbox_field) {
        case 'is_loaded':
            if (!row.driver_name || !row.driver_contact_no || !row.truck_reg_no) {
                frappe.msgprint(__('Driver name, contact, and truck registration are required before loading'));
                return false;
            }
            break;
            
        case 'is_completed':
            if (!row.truck_buying_rate || !row.transporter || !row.service_charge) {
                frappe.msgprint(__('Truck buying rate, transporter, and service charge are required before completion'));
                return false;
            }
            break;
    }
    return true;
}

function validate_milestone_date_sequence(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    const date_fields = [
        { field: 'booked_on_date', label: 'Booked Date' },
        { field: 'loaded_on_date', label: 'Loaded Date' },
        { field: 'offloaded_on_date', label: 'Offloaded Date' },
        { field: 'returned_on_date', label: 'Returned Date' },
        { field: 'completed_on_date', label: 'Completed Date' }
    ];

    let dates_with_values = [];
    let today = frappe.datetime.get_today(); // Use Frappe's date format
    let has_invalid_date = false;

    // First pass: collect and validate individual dates
    date_fields.forEach(d => {
        if (row[d.field]) {
            let date_value = row[d.field];
            
            // Normalize date to YYYY-MM-DD format
            if (typeof date_value === 'string') {
                // Handle different date formats
                if (date_value.includes('/')) {
                    // Convert DD/MM/YYYY or MM/DD/YYYY to YYYY-MM-DD
                    let parts = date_value.split('/');
                    if (parts.length === 3) {
                        // Assume DD/MM/YYYY format (adjust if your system uses MM/DD/YYYY)
                        date_value = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
                    }
                } else if (date_value.includes('-')) {
                    // Already in YYYY-MM-DD format or similar
                    date_value = date_value.split(' ')[0]; // Remove time part if present
                }
            }
            
            // Check for future dates using string comparison (works for YYYY-MM-DD format)
            if (date_value > today) {
                frappe.msgprint(__(`${d.label} cannot be in the future`));
                row[d.field] = null;
                has_invalid_date = true;
                return; // Skip this date from sequence check
            }
            
            dates_with_values.push({
                ...d,
                value: date_value,
                original_value: row[d.field]
            });
        }
    });

    // Only proceed with sequence validation if no individual date errors
    if (has_invalid_date) {
        frm.refresh_field('cargo_parcel_details');
        return;
    }

    // Second pass: check chronological order
    for (let i = 1; i < dates_with_values.length; i++) {
        if (dates_with_values[i].value < dates_with_values[i-1].value) {
            frappe.msgprint(__(`${dates_with_values[i].label} cannot be before ${dates_with_values[i-1].label}`));
            // Only clear the problematic date, not all dates
            row[dates_with_values[i].field] = null;
            frm.refresh_field('cargo_parcel_details');
            return; // Stop checking after first sequence error
        }
    }
}

function clear_all_milestones(row) {
    const milestone_fields = [
        'is_booked', 'is_loaded', 'is_offloaded', 'is_returned', 'is_completed',
        'booked_on_date', 'loaded_on_date', 'offloaded_on_date', 'returned_on_date', 'completed_on_date'
    ];
    
    milestone_fields.forEach(field => {
        row[field] = field.includes('_on_date') ? null : 0;
    });
}

// ==========================================================
// AUTO-POPULATE CARGO PARCEL DETAILS FROM PARENT (ENHANCED)
// ==========================================================

frappe.ui.form.on('Cargo Parcel Details', {
    cargo_parcel_details_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Auto-populate default values from parent Loading Master section
        if (frm.doc.is_trucking_required !== undefined) {
            frappe.model.set_value(cdt, cdn, 'is_truck_required', frm.doc.is_trucking_required);
        }
        
        if (frm.doc.road_freight_route) {
            frappe.model.set_value(cdt, cdn, 'road_freight_route', frm.doc.road_freight_route);
        }
        
        if (frm.doc.offloadiing_address) {
            frappe.model.set_value(cdt, cdn, 'cargo_offloading_address', frm.doc.offloadiing_address);
        }
        
        // Mark as auto-populated (temporary flag for this session)
        row._auto_populated = true;
        
        update_cargo_count_forwarding(frm);
    }
});

// ==========================================================
// ENHANCED PARENT VALUE CHANGE HANDLERS
// ==========================================================

frappe.ui.form.on('Forwarding Job', {
    is_trucking_required: function(frm) {
        update_all_cargo_trucking_requirement_enhanced(frm);
    },

    road_freight_route: function(frm) {
        show_route_update_dialog(frm);
    },

    offloadiing_address: function(frm) {
        show_address_update_dialog(frm);
    }
});

// Enhanced trucking requirement update (always applies to all)
function update_all_cargo_trucking_requirement_enhanced(frm) {
    if (!frm.doc.cargo_parcel_details) return;
    
    let updated = false;
    frm.doc.cargo_parcel_details.forEach(function(row) {
        if (row.is_truck_required !== frm.doc.is_trucking_required) {
            frappe.model.set_value(row.doctype, row.name, 'is_truck_required', frm.doc.is_trucking_required);
            updated = true;
        }
    });
    
    if (updated) {
        frappe.show_alert({
            message: __('Trucking requirement updated for all cargo items'),
            indicator: 'blue'
        }, 3);
    }
}

// Smart route update with user choice
function show_route_update_dialog(frm) {
    if (!frm.doc.cargo_parcel_details || !frm.doc.road_freight_route) return;
    
    // Find rows that would be affected
    const rows_using_different_route = frm.doc.cargo_parcel_details.filter(row => 
        row.road_freight_route && row.road_freight_route !== frm.doc.road_freight_route
    );
    
    const rows_using_same_route = frm.doc.cargo_parcel_details.filter(row => 
        !row.road_freight_route || row.road_freight_route === frm.doc.road_freight_route
    );

    // If no conflicts, update silently
    if (rows_using_different_route.length === 0) {
        update_cargo_routes_silently(frm, rows_using_same_route);
        return;
    }

    // Show dialog for user choice
    const dialog = new frappe.ui.Dialog({
        title: __('Update Cargo Routes'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'route_update_info',
                options: `
                    <div style="margin-bottom: 15px;">
                        <p><strong>Route changed to:</strong> ${frm.doc.road_freight_route}</p>
                        <p>Some cargo items have different routes set manually. What would you like to do?</p>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <h6>Items with different routes (${rows_using_different_route.length}):</h6>
                        <ul style="max-height: 150px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; margin: 5px 0;">
                            ${rows_using_different_route.map(row => 
                                `<li>${row.cargo_type || 'Unknown'} - ${row.container_number || row.cargo_item_description || 'Unknown'} 
                                 (Current: ${row.road_freight_route})</li>`
                            ).join('')}
                        </ul>
                    </div>
                `
            },
            {
                fieldtype: 'Select',
                fieldname: 'update_option',
                label: 'Update Option',
                options: [
                    'Update only items without specific routes',
                    'Update all items to new route',
                    'Keep existing routes unchanged'
                ].join('\n'),
                default: 'Update only items without specific routes',
                reqd: 1
            }
        ],
        primary_action_label: __('Apply'),
        primary_action(values) {
            switch(values.update_option) {
                case 'Update only items without specific routes':
                    update_cargo_routes_silently(frm, rows_using_same_route);
                    break;
                case 'Update all items to new route':
                    update_cargo_routes_silently(frm, frm.doc.cargo_parcel_details);
                    break;
                case 'Keep existing routes unchanged':
                    // FIXED: Show confirmation message but don't update anything
                    frappe.show_alert({
                        message: __('No routes were updated - existing values preserved'),
                        indicator: 'orange'
                    }, 3);
                    break;
            }
            dialog.hide();
        }
    });
    
    dialog.show();
}

// Smart address update with user choice
function show_address_update_dialog(frm) {
    if (!frm.doc.cargo_parcel_details || !frm.doc.offloadiing_address) return;
    
    // Find rows that would be affected
    const rows_using_different_address = frm.doc.cargo_parcel_details.filter(row => 
        row.cargo_offloading_address && row.cargo_offloading_address !== frm.doc.offloadiing_address
    );
    
    const rows_using_same_address = frm.doc.cargo_parcel_details.filter(row => 
        !row.cargo_offloading_address || row.cargo_offloading_address === frm.doc.offloadiing_address
    );

    // If no conflicts, update silently
    if (rows_using_different_address.length === 0) {
        update_cargo_addresses_silently(frm, rows_using_same_address);
        return;
    }

    // Show dialog for user choice
    const dialog = new frappe.ui.Dialog({
        title: __('Update Offloading Addresses'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'address_update_info',
                options: `
                    <div style="margin-bottom: 15px;">
                        <p><strong>Address changed to:</strong> ${frm.doc.offloadiing_address}</p>
                        <p>Some cargo items have different addresses set manually. What would you like to do?</p>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <h6>Items with different addresses (${rows_using_different_address.length}):</h6>
                        <ul style="max-height: 150px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; margin: 5px 0;">
                            ${rows_using_different_address.map(row => 
                                `<li>${row.cargo_type || 'Unknown'} - ${row.container_number || row.cargo_item_description || 'Unknown'} 
                                 (Current: ${row.cargo_offloading_address})</li>`
                            ).join('')}
                        </ul>
                    </div>
                `
            },
            {
                fieldtype: 'Select',
                fieldname: 'update_option',
                label: 'Update Option',
                options: [
                    'Update only items without specific addresses',
                    'Update all items to new address',
                    'Keep existing addresses unchanged'
                ].join('\n'),
                default: 'Update only items without specific addresses',
                reqd: 1
            }
        ],
        primary_action_label: __('Apply'),
        primary_action(values) {
            switch(values.update_option) {
                case 'Update only items without specific addresses':
                    update_cargo_addresses_silently(frm, rows_using_same_address);
                    break;
                case 'Update all items to new address':
                    update_cargo_addresses_silently(frm, frm.doc.cargo_parcel_details);
                    break;
                case 'Keep existing addresses unchanged':
                    // FIXED: Show confirmation message but don't update anything
                    frappe.show_alert({
                        message: __('No addresses were updated - existing values preserved'),
                        indicator: 'orange'
                    }, 3);
                    break;
            }
            dialog.hide();
        }
    });
    
    dialog.show();
}

// Helper functions for silent updates
function update_cargo_routes_silently(frm, rows_to_update) {
    let updated = false;
    rows_to_update.forEach(function(row) {
        if (row.road_freight_route !== frm.doc.road_freight_route) {
            frappe.model.set_value(row.doctype, row.name, 'road_freight_route', frm.doc.road_freight_route);
            updated = true;
        }
    });
    
    if (updated) {
        frappe.show_alert({
            message: __(`Road freight route updated for ${rows_to_update.length} cargo item(s)`),
            indicator: 'blue'
        }, 3);
    }
}

function update_cargo_addresses_silently(frm, rows_to_update) {
    let updated = false;
    rows_to_update.forEach(function(row) {
        if (row.cargo_offloading_address !== frm.doc.offloadiing_address) {
            frappe.model.set_value(row.doctype, row.name, 'cargo_offloading_address', frm.doc.offloadiing_address);
            updated = true;
        }
    });
    
    if (updated) {
        frappe.show_alert({
            message: __(`Offloading address updated for ${rows_to_update.length} cargo item(s)`),
            indicator: 'blue'
        }, 3);
    }
}