// Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

///////////////////////////////////////////////////////////////////////////////////////////////

// CALCULATE PROFIT IN TRIP DOCTYPE
frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        calculate_totals(frm);
        
        // Add modern create buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Sales Invoice'), function() {
                create_sales_invoice_from_charges(frm);
            }, __('Create'));

            frm.add_custom_button(__('Purchase Invoice'), function() {
                create_purchase_invoice_from_charges(frm);
            }, __('Create'));

            frm.add_custom_button(__('Fuel Issue'), function() {
                create_fuel_issue_from_allocation(frm);
            }, __('Create'));

            frm.add_custom_button(__('Journal Entry'), function() {
                create_journal_entry_from_other_costs(frm);
            }, __('Create'));

            frm.add_custom_button(__('Bulk Sales Invoice'), function() {
                show_bulk_invoice_dialog(frm);
            }, __('Create'));
        }
    },
    validate: function(frm) {
        calculate_totals(frm);
    },
    before_save: function(frm) {
        // Update tracking information (simplified - no milestone field)
        var lastRow = frm.doc.trip_tracking_update.slice(-1)[0];
        if (lastRow) {
            frm.set_value('current_milestone_comment', lastRow.trip_milestone_comment);
            frm.set_value('updated_on', lastRow.trip_milestone_date);
            frm.refresh();
        }
    },
    onload: function(frm) {
        if (!frm.doc.company) {
            frappe.call({
                method: "frappe.defaults.get_defaults",
                callback: function(r) {
                    if (r.message && r.message.company) {
                        frm.set_value("company", r.message.company);
                    }
                }
            });
        }
    }
});

frappe.ui.form.on('Trip Revenue Charges', {
    quantity: function(frm, cdt, cdn) {
        calculate_revenue_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_revenue_total(frm, cdt, cdn);
    },
    revenue_charges_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Fuel Allocation', {
    qty: function(frm, cdt, cdn) {
        calculate_fuel_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_fuel_total(frm, cdt, cdn);
    },
    trip_fuel_allocation_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Other Costs', {
    quantity: function(frm, cdt, cdn) {
        calculate_other_cost_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_other_cost_total(frm, cdt, cdn);
    },
    trip_other_costs_remove: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Trip Commissions', {
    quantity: function(frm, cdt, cdn) {
        calculate_commission_total(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_commission_total(frm, cdt, cdn);
    },
    trip_commissions_remove: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_revenue_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_revenue_charges');
    calculate_totals(frm);
}

function calculate_fuel_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = row.qty * row.rate;
    frm.refresh_field('trip_fuel_allocation');
    calculate_totals(frm);
}

function calculate_other_cost_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_other_costs');
    calculate_totals(frm);
}

function calculate_commission_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total_amount = row.quantity * row.rate;
    frm.refresh_field('trip_commissions');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_revenue = 0;
    let total_fuel_cost = 0;
    let total_other_costs = 0;
    let total_commissions = 0;

    (frm.doc.trip_revenue_charges || []).forEach(d => {
        total_revenue += d.total_amount || 0;
    });

    (frm.doc.trip_fuel_allocation || []).forEach(d => {
        total_fuel_cost += d.amount || 0;
    });

    (frm.doc.trip_other_costs || []).forEach(d => {
        total_other_costs += d.total_amount || 0;
    });

    (frm.doc.trip_commissions || []).forEach(d => {
        total_commissions += d.total_amount || 0;
    });

    const total_cost = total_fuel_cost + total_other_costs + total_commissions;
    const profit = total_revenue - total_cost;

    frm.set_value('total_estimated_revenue', total_revenue);
    frm.set_value('total_estimated_cost', total_cost);
    frm.set_value('estimated_profit', profit);
}

//////////////////////////////////////////////////////////////////////////////////////////
//UPDATE CURRENT MILESTONE
frappe.ui.form.on('Trip', {
    before_save: function(frm) {
        var lastRow = frm.doc.trip_tracking_update.slice(-1)[0];
        if (lastRow) {
            frm.set_value('current_milestone_comment', lastRow.trip_milestone_comment);
            frm.set_value('updated_on', lastRow.trip_milestone_date);
            frm.refresh();
        }
    }
});

/////////////////////////////////////////////////////////////////////////////////////////////////
//FILTER ROUTES BASED ON DIRECTION SELECTED AND ONLY SHOW ACTIVE ROUTES
frappe.ui.form.on('Trip', {
    setup: function(frm) {
        frm.set_query('route', function() {
            if (frm.doc.trip_direction) {
                return {
                    filters: {
                        'trip_direction': frm.doc.trip_direction,
                        'is_deactivated': 0
                    }
                };
            } else {
                return {
                    filters: {
                        'is_deactivated': 0
                    }
                };
            }
        });
    }
});

//////////////////////////////////////////////////////////////////////////////
// SALES INVOICE CREATION
function create_sales_invoice_from_charges(frm) {
    const all_rows = frm.doc.trip_revenue_charges || [];
    const eligible_rows = all_rows.filter(row => 
        row.rate && row.receivable_party && !row.is_invoiced
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible revenue charges found for invoicing."));
        return;
    }

    let selected_customer = eligible_rows[0].receivable_party;

    const get_unique_customers = () => [...new Set(eligible_rows.map(r => r.receivable_party))];

    const render_dialog_ui = (dialog, customer) => {
        const customers = get_unique_customers();
        const rows = customer ? eligible_rows.filter(r => r.receivable_party === customer) : eligible_rows;

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

        // In the render_dialog_ui function, update the table structure:
        const table = `
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead style="background-color: #f8f9fa; position: sticky; top: 0; z-index: 10;">
                        <tr>
                            <th style="width: 40px; text-align: center;">
                                <input type="checkbox" id="select-all-charges" title="Select All">
                            </th>
                            <th style="width: 200px;">Customer</th>
                            <th style="width: 150px;">Charge</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 120px; text-align: right;">Rate</th>
                            <th style="width: 120px; text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
                                </td>
                                <td>${row.receivable_party || ''}</td>
                                <td>${row.charge || ''}</td>
                                <td style="text-align: right;">${frappe.format(row.quantity || 0, { fieldtype: 'Float', precision: 2 })}</td>
                                <td style="text-align: right;">${frappe.format(row.rate || 0, { fieldtype: 'Currency', precision: 2 })}</td>
                                <td style="text-align: right;">${frappe.format(row.total_amount || 0, { fieldtype: 'Currency', precision: 2 })}</td>
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
            const unique_customers = [...new Set(selected_rows.map(r => r.receivable_party))];

            if (unique_customers.length > 1) {
                frappe.msgprint(__("You can only create an invoice for one customer at a time."));
                return;
            }

            frappe.call({
                method: "freightmas.trucking_service.doctype.trip.trip.create_sales_invoice",
                args: {
                    trip_name: frm.doc.name,
                    selected_charges: selected,
                    receivable_party: unique_customers[0]
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Sales Invoice Created'),
                            message: __('Sales Invoice {0} has been created successfully', [r.message.invoice_name]),
                            indicator: 'green'
                        });
                        
                        frappe.set_route("Form", "Sales Invoice", r.message.invoice_name);
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

//////////////////////////////////////////////////////////////////////////
// PURCHASE INVOICE CREATION
function create_purchase_invoice_from_charges(frm) {
    const all_rows = frm.doc.trip_cost_charges || [];
    const eligible_rows = all_rows.filter(row => 
        row.rate && row.payable_party && !row.is_invoiced
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible cost charges found for purchase invoicing."));
        return;
    }

    let selected_supplier = eligible_rows[0].payable_party;

    const get_unique_suppliers = () => [...new Set(eligible_rows.map(r => r.payable_party))];

    const render_dialog_ui = (dialog, supplier) => {
        const suppliers = get_unique_suppliers();
        const rows = supplier ? eligible_rows.filter(r => r.payable_party === supplier) : eligible_rows;

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
                            <th style="min-width: 200px;">Description</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Rate</th>
                            <th style="width: 100px; text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
                                </td>
                                <td>${row.payable_party || ''}</td>
                                <td>${row.charge || ''}</td>
                                <td>${row.charge_description || ''}</td>
                                <td style="text-align: right;">${row.quantity || 0}</td>
                                <td style="text-align: right;">${frappe.format(row.rate || 0, { fieldtype: 'Currency' })}</td>
                                <td style="text-align: right;">${frappe.format(row.total_amount || 0, { fieldtype: 'Currency' })}</td>
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
            const unique_suppliers = [...new Set(selected_rows.map(r => r.payable_party))];

            if (unique_suppliers.length > 1) {
                frappe.msgprint(__("You can only create an invoice for one supplier at a time."));
                return;
            }

            frappe.call({
                method: "freightmas.trucking_service.doctype.trip.trip.create_purchase_invoice",
                args: {
                    trip_name: frm.doc.name,
                    selected_charges: selected,
                    supplier: unique_suppliers[0]
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Purchase Invoice Created'),
                            message: __('Purchase Invoice {0} has been created successfully', [r.message.invoice_name]),
                            indicator: 'green'
                        });
                        
                        frappe.set_route("Form", "Purchase Invoice", r.message.invoice_name);
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

//////////////////////////////////////////////////////////////
// FUEL ISSUE CREATION
function create_fuel_issue_from_allocation(frm) {
    const all_rows = frm.doc.trip_fuel_allocation || [];
    const eligible_rows = all_rows.filter(row => 
        !row.is_invoiced && !row.stock_entry_reference
    );

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible fuel allocation rows found."));
        return;
    }

    const table = `
        <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
            <table class="table table-bordered table-sm" style="margin: 0;">
                <thead style="background-color: #f8f9fa; position: sticky;
                    <tr>
                        <th style="width: 40px; text-align: center;">
                            <input type="checkbox" id="select-all-fuel" title="Select All">
                        </th>
                        <th style="min-width: 150px;">Item</th>
                        <th style="width: 100px; text-align: right;">Qty (L)</th>
                        <th style="width: 100px; text-align: right;">Rate</th>
                        <th style="width: 100px; text-align: right;">Amount</th>
                        <th style="min-width: 150px;">Warehouse</th>
                    </tr>
                </thead>
                <tbody>
                    ${eligible_rows.map(row => `
                        <tr>
                            <td style="text-align: center;">
                                <input type="checkbox" class="fuel-row-check" data-row-name="${row.name}">
                            </td>
                            <td>${row.item || ''}</td>
                            <td style="text-align: right;">${row.qty || 0}</td>
                            <td style="text-align: right;">${frappe.format(row.rate || 0, { fieldtype: 'Currency' })}</td>
                            <td style="text-align: right;">${frappe.format((row.qty * row.rate) || 0, { fieldtype: 'Currency' })}</td>
                            <td>${row.s_warehouse || ''}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    const dialog = new frappe.ui.Dialog({
        title: __('Select Fuel Allocation Rows'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'fuel_rows_html',
                options: table
            }
        ],
        primary_action_label: __('Create Stock Entry'),
        primary_action() {
            const selected = Array.from(
                dialog.$wrapper.find('.fuel-row-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one row."));
                return;
            }

            frappe.call({
                method: "freightmas.trucking_service.doctype.trip.trip.create_fuel_stock_entry_with_rows",
                args: {
                    docname: frm.doc.name,
                    row_names: selected
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Stock Entry Created'),
                            message: __('Stock Entry {0} has been created successfully', [r.message]),
                            indicator: 'green'
                        });
                        
                        frappe.set_route("Form", "Stock Entry", r.message);
                        frm.reload_doc();
                        dialog.hide();
                    }
                }
            });
        }
    });

    dialog.show();

    // Select all checkbox handler
    dialog.$wrapper.find('#select-all-fuel').on('change', function() {
        const isChecked = this.checked;
        dialog.$wrapper.find('.fuel-row-check').prop('checked', isChecked);
    });

    // Individual checkbox handler
    dialog.$wrapper.find('.fuel-row-check').on('change', function() {
        const total = dialog.$wrapper.find('.fuel-row-check').length;
        const checked = dialog.$wrapper.find('.fuel-row-check:checked').length;
        dialog.$wrapper.find('#select-all-fuel').prop('checked', total === checked);
    });
}

//////////////////////////////////////////////////////////////
// SIMPLIFIED OTHER CHARGES JOURNAL ENTRY CREATION - CORRECT FIELD MAPPING
function create_journal_entry_from_other_costs(frm) {
    const all_rows = frm.doc.trip_other_costs || [];
    
    // Debug: Let's see what we're working with
    console.log("All rows:", all_rows);
    
    const eligible_rows = all_rows.filter(row => {
        const has_amount = row.total_amount && row.total_amount > 0;
        const not_invoiced = !row.is_invoiced;
        const no_journal = !row.journal_entry;
        
        console.log(`Row ${row.name}: total_amount=${row.total_amount}, is_invoiced=${row.is_invoiced}, journal_entry=${row.journal_entry}`);
        
        return has_amount && not_invoiced && no_journal;
    });

    console.log("Eligible rows found:", eligible_rows.length);

    if (!eligible_rows.length) {
        frappe.msgprint(__("No eligible 'Other Costs' rows found for journal entry creation."));
        return;
    }

    const table = `
        <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
            <table class="table table-bordered table-sm" style="margin: 0;">
                <thead style="background-color: #f8f9fa; position: sticky; top: 0; z-index: 10;">
                    <tr>
                        <th style="width: 40px; text-align: center;">
                            <input type="checkbox" id="select-all-costs" title="Select All">
                        </th>
                        <th style="min-width: 150px;">Charge</th>
                        <th style="width: 100px; text-align: right;">Amount</th>
                        <th style="min-width: 150px;">Expense Account</th>
                        <th style="min-width: 150px;">Contra Account</th>
                    </tr>
                </thead>
                <tbody>
                    ${eligible_rows.map(row => {
                        const has_accounts = row.expense_account && row.contra_account;
                        
                        return `
                            <tr ${!has_accounts ? 'style="background-color: #fff3cd;"' : ''}>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="other-costs-check" data-row-name="${row.name}" ${!has_accounts ? 'disabled' : ''}>
                                </td>
                                <td>${row.item_code || 'N/A'}</td>
                                <td style="text-align: right;">${frappe.format(row.total_amount || 0, { fieldtype: 'Currency' })}</td>
                                <td>${row.expense_account || '<span style="color: red;">Missing</span>'}</td>
                                <td>${row.contra_account || '<span style="color: red;">Missing</span>'}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;

    const dialog = new frappe.ui.Dialog({
        title: __('Select Other Charges for Journal Entry'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'other_costs_html',
                options: table
            }
        ],
        primary_action_label: __('Create Journal Entry'),
        primary_action() {
            const selected = Array.from(
                dialog.$wrapper.find('.other-costs-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one row."));
                return;
            }

            frappe.call({
                method: "freightmas.trucking_service.doctype.trip.trip.create_journal_entry_from_other_costs",
                args: {
                    trip_name: frm.doc.name,
                    selected_charges: selected
                },
                callback(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Journal Entry Created'),
                            message: __('Journal Entry {0} has been created successfully', [r.message]),
                            indicator: 'green'
                        });
                        
                        frappe.set_route("Form", "Journal Entry", r.message);
                        frm.reload_doc();
                        dialog.hide();
                    }
                },
                error(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Failed to create Journal Entry. Please check the console for details.'),
                        indicator: 'red'
                    });
                    console.error('Journal Entry Creation Error:', r);
                }
            });
        }
    });

    dialog.show();

    // Select all checkbox handler (only enabled checkboxes)
    dialog.$wrapper.find('#select-all-costs').on('change', function() {
        const isChecked = this.checked;
        dialog.$wrapper.find('.other-costs-check:not(:disabled)').prop('checked', isChecked);
    });

    // Individual checkbox handler
    dialog.$wrapper.find('.other-costs-check').on('change', function() {
        const total = dialog.$wrapper.find('.other-costs-check:not(:disabled)').length;
        const checked = dialog.$wrapper.find('.other-costs-check:checked').length;
        dialog.$wrapper.find('#select-all-costs').prop('checked', total === checked);
    });
}

//////////////////////////////////////////////////////////////////////////
//PREVENT DELETION OF INVOICED REVENUE CHARGES
frappe.ui.form.on('Trip Revenue Charges', {
    before_trip_revenue_charges_remove: function (frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.is_invoiced) {
            frappe.throw(__("You cannot delete an invoiced charge."));
        }
    }
});

////////////////////////////////////////////////////////////////////////////////////
//PREVENT DELETION OF INVOICED COST CHARGES
frappe.ui.form.on('Trip Cost Charges', {
    before_trip_cost_charges_remove: function (frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.is_invoiced) {
            frappe.throw(__("You cannot delete an invoiced charge."));
        }
    }
});

//////////////////////////////////////////////////////////////////////////////////////
// Auto-fetch fuel rate based on selected item and warehouse in Trip Fuel Allocation
frappe.ui.form.on('Trip Fuel Allocation', {
    item: fetch_fuel_rate,
    s_warehouse: fetch_fuel_rate
});

function fetch_fuel_rate(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.item && row.s_warehouse) {
        frappe.call({
            method: "freightmas.api.get_fuel_rate",
            args: {
                item_code: row.item,
                warehouse: row.s_warehouse
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "rate", r.message);
                }
            }
        });
    }
}


//////////////////////////////////////////////////////////////
//Prevent Deletion of Issued Rows
frappe.ui.form.on('Trip Fuel Allocation', {
    before_trip_fuel_allocation_remove: function (frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.is_invoiced || row.stock_entry_reference) {
            frappe.throw(__("You cannot delete a fuel allocation that has already been issued."));
        }
    }
});

// ==============================
// PREVENT DELETION OF JOURNALED ROWS
// ==============================
frappe.ui.form.on('Trip Other Costs', {
    before_trip_other_costs_remove(frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.journal_entry) {
            frappe.throw(__("You cannot delete a cost row linked to a Journal Entry."));
        }
    }
});

///////////////////////////////////////////////////
// FILTER ACCOUNTS BASED ON COMPANY
// AND DISABLE "Create New" FROM LINK FIELD
// IN TRIP OTHER COSTS DOCTYPE
// This ensures that only accounts from the selected company are available for selection.

frappe.ui.form.on('Trip', {
    onload: function(frm) {
        set_account_filters(frm);
    },
    company: function(frm) {
        set_account_filters(frm);
    }
});

function set_account_filters(frm) {
    const fields = ['expense_account', 'contra_account'];

    fields.forEach(field => {
        frappe.meta.get_docfield('Trip Other Costs', field, frm.doc.name).get_query = function(doc, cdt, cdn) {
            const company = frm.doc.company || frappe.defaults.get_default("company");
            return {
                filters: {
                    company: company,
                    is_group: 0
                }
            };
        };

        // Disable "Create New" from link field
        frappe.meta.get_docfield('Trip Other Costs', field, frm.doc.name).only_select = 1;
    });
}
////////////////////////////////////////////////////////
//Set Truck field in Child Tables from Parent Doctype

// Revenue Charges
frappe.ui.form.on('Trip Revenue Charges', {
    trip_revenue_charges_add: function(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'truck', frm.doc.truck);
    }
});

// Fuel Allocation
frappe.ui.form.on('Trip Fuel Allocation', {
    trip_fuel_allocation_add: function(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'truck', frm.doc.truck);
        frappe.model.set_value(cdt, cdn, 's_warehouse', frm.doc.s_warehouse);
    }
});

// Other Costs
frappe.ui.form.on('Trip Other Costs', {
    trip_other_costs_add: function(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'truck', frm.doc.truck);
    }
});

//////////////////////////////////////////////////
// Create Bulk Sales Invoice


function show_bulk_invoice_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Bulk Sales Invoice Creation'),
        size: 'large',
        fields: [
            { fieldtype: 'Section Break', label: __('Filters') },

            // Row 1
            {
                fieldtype: 'Link',
                fieldname: 'customer',
                label: 'Customer',
                options: 'Customer',
                default: frm.doc.customer,
                onchange: () => fetch_trips()
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Link',
                fieldname: 'route',
                label: 'Route',
                options: 'Route',
                default: frm.doc.route,
                onchange: () => fetch_trips()
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Link',
                fieldname: 'cargo_type',
                label: 'Cargo Type',
                options: 'Cargo Type',
                default: frm.doc.cargo_type,
                onchange: () => fetch_trips()
            },

            // Row 2
            { fieldtype: 'Section Break' },
            {
                fieldtype: 'Link',
                fieldname: 'trip_direction',
                label: 'Trip Direction',
                options: 'Trip Direction',
                default: frm.doc.trip_direction,
                onchange: () => fetch_trips()
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Date',
                fieldname: 'from_date',
                label: 'From Date',
                default: frappe.datetime.add_days(frappe.datetime.get_today(), -29),
                onchange: () => fetch_trips()
            },
            { fieldtype: 'Column Break' },
            {
                fieldtype: 'Date',
                fieldname: 'to_date',
                label: 'To Date',
                default: frappe.datetime.get_today(),
                onchange: () => fetch_trips()
            },

            { fieldtype: 'Section Break' },
            { fieldtype: 'HTML', fieldname: 'trips_html' },
            {
                fieldtype: 'Check',
                fieldname: 'group_invoice',
                label: 'Group into Single Invoice',
                default: 1
            }
        ],
        primary_action_label: __('Create Invoices'),
        primary_action: function() {
            // Collect selected charges
            let selected = Array.from(dialog.$wrapper.find('.charge-row-check:checked')).map(el => ({
                trip: el.dataset.tripName,
                charge: el.dataset.chargeName
            }));

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one charge."));
                return;
            }

            frappe.call({
                method: "freightmas.trucking_service.doctype.trip.trip.create_bulk_invoices",
                args: {
                    selected_charges: selected,
                    group_invoice: dialog.get_value('group_invoice') ? 1 : 0
                },
                freeze: true,
                freeze_message: __("Creating Invoices..."),
                callback: function(r) {
                    if (r.message) {
                        let msg = `Created and submitted ${r.message.invoices.length} invoice(s).`;
                        if (r.message.bulk_invoice) {
                            msg += `<br>Created Bulk Invoice: ${r.message.bulk_invoice}`;
                            frappe.set_route("Form", "Trip Bulk Sales Invoice", r.message.bulk_invoice);
                        }
                        frappe.show_alert({ message: msg, indicator: 'green' });
                        frm.reload_doc();
                        dialog.hide();
                    }
                }
            });
        }
    });

    function fetch_trips() {
        let filters = {
            customer: dialog.get_value('customer'),
            route: dialog.get_value('route'),
            trip_direction: dialog.get_value('trip_direction'),
            cargo_type: dialog.get_value('cargo_type'),
            from_date: dialog.get_value('from_date'),
            to_date: dialog.get_value('to_date')
        };

        frappe.call({
            method: "freightmas.trucking_service.doctype.trip.trip.get_uninvoiced_trips",
            args: { filters },
            callback: function(r) {
                render_trips_table(r.message || []);
            }
        });
    }

    function render_trips_table(trips) {
        let html = `
            <div style="max-height: 350px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
                <table class="table table-bordered table-sm" style="margin: 0;">
                    <thead>
                        <tr>
                            <th style="width: 40px; text-align: center;">
                                <input type="checkbox" id="select-all-charges" title="Select All">
                            </th>
                            <th>Trip</th>
                            <th>Truck</th>
                            <th>Charge</th>
                            <th>Qty</th>
                            <th>Rate</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${
                            trips.map(trip => {
                                if (!trip.revenue_charges || !trip.revenue_charges.length) return '';
                                return trip.revenue_charges
                                    .map(charge => `
                                        <tr>
                                            <td style="text-align: center;">
                                                <input type="checkbox" class="charge-row-check" data-trip-name="${trip.name}" data-charge-name="${charge.name}">
                                            </td>
                                            <td>${trip.name}</td>
                                            <td>${charge.truck || ''}</td> <!-- Corrected line -->
                                            <td>${charge.charge || ''}</td>
                                            <td>${frappe.format(charge.quantity || 0, { fieldtype: 'Float', precision: 2 })}</td>
                                            <td>${frappe.format(charge.rate || 0, { fieldtype: 'Currency', precision: 2 })}</td>
                                            <td>${frappe.format(charge.total_amount || 0, { fieldtype: 'Currency', precision: 2 })}</td>
                                        </tr>
                                    `).join('');
                            }).join('')
                        }
                    </tbody>
                </table>
            </div>
            ${
                trips.every(trip => !trip.revenue_charges || !trip.revenue_charges.length)
                ? '<p style="text-align: center; color: #999; margin-top: 20px;">No eligible charges found for the selected filters.</p>'
                : ''
            }
        `;
        dialog.fields_dict.trips_html.$wrapper.html(html);

        // Select all handler
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
    }

    fetch_trips();
    dialog.show();
}