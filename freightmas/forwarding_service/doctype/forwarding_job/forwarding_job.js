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
                navigator.clipboard.writeText(url).then(() => {
                    frappe.show_alert({
                        message: __('Portal link copied to clipboard!'),
                        indicator: 'green'
                    }, 5);
                }).catch(err => {
                    frappe.msgprint(__('Failed to copy: ') + err);
                });
            }, __('View'));
        }

        // ========================================
        // PORTAL ACTIVE INDICATOR
        // ========================================
        if (frm.doc.share_with_road_freight && !frm.is_new()) {
            const html = `
                <div style="display: flex; align-items: center;">
                    <span style="font-weight: bold;">🌐 Web Portal Active</span>
                    <a href="${window.location.origin}/truck_portal?job=${frm.doc.name}" 
                       target="_blank" 
                       style="color: white; text-decoration: underline; margin-left: 10px;">
                        View Portal →
                    </a>
                </div>`;
            // correct usage: object + timeout (seconds)
            frappe.show_alert({ message: html, indicator: 'blue' }, 5);
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
    
    share_with_road_freight: function(frm) {
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
