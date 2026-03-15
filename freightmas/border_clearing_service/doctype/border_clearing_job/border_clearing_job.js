// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// ==========================================================
// Border Clearing Job - Client Script
// ==========================================================

frappe.ui.form.on('Border Clearing Job', {
    refresh: function(frm) {
        toggle_milestone_dates(frm);
        render_progress_dial_and_theme_chips(frm);
        toggle_base_fields(frm);
        update_currency_labels(frm);
        toggle_costing_table_lock(frm);

        // Custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Create Sales Invoice'), function() {
                create_sales_invoice_from_charges(frm);
            }, __('Create'));

            frm.add_custom_button(__('Create Purchase Invoice'), function() {
                create_purchase_invoice_from_charges(frm);
            }, __('Create'));
        }
    },

    // Revenue Recognition - Set Date Button
    set_rr_date: function(frm) {
        show_recognition_date_dialog(frm);
    },

    // Milestone checkbox triggers
    is_documents_received: toggle_milestone_dates,
    is_entry_lodged: toggle_milestone_dates,
    is_duty_assessed: toggle_milestone_dates,
    is_duty_paid: toggle_milestone_dates,
    is_examination_required: toggle_milestone_dates,
    is_examination_done: toggle_milestone_dates,
    is_release_obtained: toggle_milestone_dates,
    is_cleared: toggle_milestone_dates,

    validate: function(frm) {
        let missing_fields = [];

        const check_date = (checkbox, date_field, label) => {
            if (frm.doc[checkbox] && !frm.doc[date_field]) {
                missing_fields.push(label);
            }
        };

        check_date("is_documents_received", "documents_received_date", "Documents Received Date");
        check_date("is_entry_lodged", "entry_lodged_date", "Entry Lodged Date");
        check_date("is_duty_assessed", "duty_assessed_date", "Duty Assessed Date");
        check_date("is_duty_paid", "duty_paid_date", "Duty Paid Date");
        check_date("is_release_obtained", "release_date", "Release Date");
        check_date("is_cleared", "cleared_date", "Cleared Date");

        if (frm.doc.is_examination_required && frm.doc.is_examination_done && !frm.doc.examination_date) {
            missing_fields.push("Examination Date");
        }

        if (missing_fields.length > 0) {
            frappe.throw(
                __("Please fill the following required fields:<br><ul><li>{0}</li></ul>",
                    [missing_fields.join("</li><li>")])
            );
        }

        calculate_costing_totals(frm);
        calculate_actual_totals(frm);
    },

    currency: function(frm) {
        if (frm.doc.currency && frm.doc.base_currency && frm.doc.currency !== frm.doc.base_currency) {
            frappe.call({
                method: "erpnext.setup.utils.get_exchange_rate",
                args: {
                    from_currency: frm.doc.currency,
                    to_currency: frm.doc.base_currency
                },
                callback: function(r) {
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

    conversion_rate: function(frm) {
        calculate_costing_totals(frm);
        calculate_actual_totals(frm);
    },

    base_currency: function(frm) {
        update_currency_labels(frm);
        toggle_base_fields(frm);
    },

    status: function(frm) {
        toggle_costing_table_lock(frm);
    },

    before_save: function(frm) {
        const tracking = frm.doc.border_clearing_tracking;
        if (tracking && tracking.length > 0) {
            const last = tracking[tracking.length - 1];
            set_main_value_safe(frm, 'current_comment', last.comment);
            set_main_value_safe(frm, 'last_updated_on', last.updated_on);
            set_main_value_safe(frm, 'last_updated_by', last.updated_by);
        }
    },

    // Template loading button
    load_charges_from_template(frm) {
        open_charges_template_dialog(frm);
    },

    // Fetch from costing buttons
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
    }
});

// ==========================================================
// Milestone Tracker UI Refresh Triggers
// ==========================================================
[
    "is_documents_received", "is_entry_lodged", "is_duty_assessed",
    "is_duty_paid", "is_examination_required", "is_examination_done",
    "is_release_obtained", "is_cleared"
].forEach(field => {
    frappe.ui.form.on('Border Clearing Job', {
        [`${field}`]: function(frm) {
            render_progress_dial_and_theme_chips(frm);
        }
    });
});

// ==========================================================
// BORDER CLEARING COSTING CHARGES
// ==========================================================
frappe.ui.form.on('Border Clearing Costing Charges', {
    border_clearing_costing_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_costing_totals(frm);
    },

    border_clearing_costing_charges_remove: function(frm) {
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
    },

    is_pass_through: function(frm) {
        calculate_costing_totals(frm);
    }
});

// ==========================================================
// BORDER CLEARING REVENUE CHARGES
// ==========================================================
frappe.ui.form.on('Border Clearing Revenue Charges', {
    border_clearing_revenue_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_actual_totals(frm);
    },

    border_clearing_revenue_charges_remove: function(frm) {
        calculate_actual_totals(frm);
    },

    qty: function(frm, cdt, cdn) {
        calculate_revenue_charge_amounts(frm, cdt, cdn);
    },

    sell_rate: function(frm, cdt, cdn) {
        calculate_revenue_charge_amounts(frm, cdt, cdn);
    },

    is_pass_through: function(frm) {
        calculate_actual_totals(frm);
    },

    form_render(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const grid_row = frm.fields_dict.border_clearing_revenue_charges.grid.grid_rows_by_docname[cdn];
        if (row?.sales_invoice_reference) {
            grid_row.columns.forEach(col => {
                if (col.df.fieldname !== 'sales_invoice_reference') {
                    col.df.read_only = 1;
                }
            });
            grid_row.refresh();
        }
    },

    before_border_clearing_revenue_charges_remove(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row?.sales_invoice_reference) {
            frappe.throw(__('Cannot delete a revenue charge linked to Sales Invoice {0}.', [row.sales_invoice_reference]));
        }
    }
});

// ==========================================================
// BORDER CLEARING COST CHARGES
// ==========================================================
frappe.ui.form.on('Border Clearing Cost Charges', {
    border_clearing_cost_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_actual_totals(frm);
    },

    border_clearing_cost_charges_remove: function(frm) {
        calculate_actual_totals(frm);
    },

    qty: function(frm, cdt, cdn) {
        calculate_cost_charge_amounts(frm, cdt, cdn);
    },

    buy_rate: function(frm, cdt, cdn) {
        calculate_cost_charge_amounts(frm, cdt, cdn);
    },

    is_pass_through: function(frm) {
        calculate_actual_totals(frm);
    },

    form_render(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const grid_row = frm.fields_dict.border_clearing_cost_charges.grid.grid_rows_by_docname[cdn];
        if (row?.purchase_invoice_reference) {
            grid_row.columns.forEach(col => {
                if (col.df.fieldname !== 'purchase_invoice_reference') {
                    col.df.read_only = 1;
                }
            });
            grid_row.refresh();
        }
    },

    before_border_clearing_cost_charges_remove(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row?.purchase_invoice_reference) {
            frappe.throw(__('Cannot delete a cost charge linked to Purchase Invoice {0}.', [row.purchase_invoice_reference]));
        }
    }
});

// ==========================================================
// CALCULATION FUNCTIONS
// ==========================================================

function calculate_costing_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let qty = flt(row.qty) || 1;
    let sell_rate = flt(row.sell_rate) || 0;
    let buy_rate = flt(row.buy_rate) || 0;

    let revenue_amount = flt(qty * sell_rate, 2);
    let cost_amount = flt(qty * buy_rate, 2);
    let margin_amount = flt(revenue_amount - cost_amount, 2);
    let margin_percentage = revenue_amount > 0 ? flt((margin_amount / revenue_amount * 100), 2) : 0;

    frappe.model.set_value(cdt, cdn, 'revenue_amount', revenue_amount);
    frappe.model.set_value(cdt, cdn, 'cost_amount', cost_amount);
    frappe.model.set_value(cdt, cdn, 'margin_amount', margin_amount);
    frappe.model.set_value(cdt, cdn, 'margin_percentage', margin_percentage);

    calculate_costing_totals(frm);
}

function calculate_costing_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;
    let total_pass_through = 0;

    $.each(frm.doc.border_clearing_costing_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
        total_cost += flt(row.cost_amount);
        if (row.is_pass_through) {
            total_pass_through += flt(row.revenue_amount);
        }
    });

    let total_profit = flt(total_revenue - total_cost, 2);
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? flt((total_profit / total_revenue * 100), 2) : 0;

    set_main_value_safe(frm, 'total_quoted_revenue', flt(total_revenue, 2));
    set_main_value_safe(frm, 'total_quoted_cost', flt(total_cost, 2));
    set_main_value_safe(frm, 'total_quoted_margin', total_profit);
    set_main_value_safe(frm, 'quoted_margin_percent', profit_margin_percent);
    set_main_value_safe(frm, 'total_quoted_duty_pass_through', flt(total_pass_through, 2));

    set_main_value_safe(frm, 'total_quoted_revenue_base', flt(total_revenue * rate, 2));
    set_main_value_safe(frm, 'total_quoted_cost_base', flt(total_cost * rate, 2));
    set_main_value_safe(frm, 'total_quoted_profit_base', flt(total_profit * rate, 2));

    frm.refresh_fields();
}

function calculate_revenue_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let qty = flt(row.qty) || 1;
    let sell_rate = flt(row.sell_rate) || 0;
    let revenue_amount = flt(qty * sell_rate, 2);

    frappe.model.set_value(cdt, cdn, 'revenue_amount', revenue_amount);
    calculate_actual_totals(frm);
}

function calculate_cost_charge_amounts(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let qty = flt(row.qty) || 1;
    let buy_rate = flt(row.buy_rate) || 0;
    let cost_amount = flt(qty * buy_rate, 2);

    frappe.model.set_value(cdt, cdn, 'cost_amount', cost_amount);
    calculate_actual_totals(frm);
}

function calculate_actual_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;
    let total_pass_through = 0;

    $.each(frm.doc.border_clearing_revenue_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
        if (row.is_pass_through) {
            total_pass_through += flt(row.revenue_amount);
        }
    });

    $.each(frm.doc.border_clearing_cost_charges || [], function(i, row) {
        total_cost += flt(row.cost_amount);
    });

    let total_profit = total_revenue - total_cost;
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? (total_profit / total_revenue * 100) : 0;

    set_main_value_safe(frm, 'total_working_revenue', total_revenue);
    set_main_value_safe(frm, 'total_working_cost', total_cost);
    set_main_value_safe(frm, 'total_working_profit', total_profit);
    set_main_value_safe(frm, 'profit_margin_percent', profit_margin_percent);
    set_main_value_safe(frm, 'total_working_duty_pass_through', flt(total_pass_through, 2));

    set_main_value_safe(frm, 'total_working_revenue_base', total_revenue * rate);
    set_main_value_safe(frm, 'total_working_base', total_cost * rate);
    set_main_value_safe(frm, 'total_working_profit_base', total_profit * rate);

    frm.refresh_fields();
}

// ==========================================================
// COSTING TABLE LOCK
// ==========================================================

function toggle_costing_table_lock(frm) {
    const fieldname = 'border_clearing_costing_charges';
    const is_draft = frm.doc.status === 'Draft';

    if (!frm.fields_dict[fieldname]) return;

    frm.set_df_property(fieldname, 'cannot_add_rows', !is_draft);
    frm.set_df_property(fieldname, 'allow_bulk_edit', is_draft);

    const grid_field = frm.fields_dict[fieldname];
    const grid = grid_field && grid_field.grid;
    const wrapper = grid_field.$wrapper;

    if (!grid) return;

    grid.df.read_only = !is_draft;

    if (!is_draft) {
        wrapper.find('.grid-add-row, .grid-duplicate-row, .grid-delete-row, .grid-expand-row').hide();

        try {
            if (grid.grid_rows_by_docname) {
                Object.keys(grid.grid_rows_by_docname).forEach(name => {
                    const grid_row = grid.grid_rows_by_docname[name];
                    if (!grid_row || !grid_row.columns) return;
                    grid_row.columns.forEach(col => {
                        if (col && col.df) col.df.read_only = 1;
                    });
                    grid_row.refresh();
                });
            } else {
                wrapper.find('.grid-body').css({'pointer-events': 'none', 'opacity': 0.7});
            }
        } catch (e) {
            console.warn('Error locking costing grid rows', e);
        }

        if (!wrapper.find('.fm-costing-locked').length) {
            wrapper.find('.grid-heading-row').after(
                `<div class="fm-costing-locked"
                      style="padding:6px 0 4px 0; margin-top:4px; color:#0b5ed7; font-weight:500; font-size:13px;">
                    Planned Job Costing is locked for editing to maintain budget figures.
                </div>`
            );
        }
    } else {
        wrapper.find('.fm-costing-locked').remove();
        wrapper.find('.grid-add-row, .grid-duplicate-row, .grid-delete-row, .grid-expand-row').show();
        wrapper.find('.grid-body').css({'pointer-events': '', 'opacity': ''});

        try {
            if (grid.grid_rows_by_docname) {
                Object.keys(grid.grid_rows_by_docname).forEach(name => {
                    const grid_row = grid.grid_rows_by_docname[name];
                    if (!grid_row || !grid_row.columns) return;
                    grid_row.columns.forEach(col => {
                        if (col && col.df) col.df.read_only = 0;
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
// Show/Hide Base Currency Fields
// ==========================================================

function toggle_base_fields(frm) {
    const show = frm.doc.currency !== frm.doc.base_currency;

    frm.toggle_display('total_quoted_revenue_base', show);
    frm.toggle_display('total_quoted_cost_base', show);
    frm.toggle_display('total_quoted_profit_base', show);

    frm.toggle_display('total_working_revenue_base', show);
    frm.toggle_display('total_working_base', show);
    frm.toggle_display('total_working_profit_base', show);
}

// ==========================================================
// Update Currency Labels
// ==========================================================

function update_currency_labels(frm) {
    const currency = frm.doc.currency || "USD";
    const base_currency = frm.doc.base_currency || "USD";

    const costing_labels = {
        total_quoted_revenue: `Total Quoted Revenue (${currency})`,
        total_quoted_cost: `Total Quoted Cost (${currency})`,
        total_quoted_margin: `Total Quoted Profit (${currency})`,
        total_quoted_duty_pass_through: `Quoted Duty Pass-Through (${currency})`,
        total_quoted_revenue_base: `Total Quoted Revenue (${base_currency})`,
        total_quoted_cost_base: `Total Quoted Cost (${base_currency})`,
        total_quoted_profit_base: `Total Quoted Profit (${base_currency})`
    };

    const actuals_labels = {
        total_working_revenue: `Working Revenue (${currency})`,
        total_working_cost: `Working Cost (${currency})`,
        total_working_profit: `Total Working Margin (${currency})`,
        total_working_duty_pass_through: `Working Duty Pass-Through (${currency})`,
        total_working_revenue_base: `Total Working Revenue (${base_currency})`,
        total_working_base: `Total Working Cost (${base_currency})`,
        total_working_profit_base: `Total Working Margin (${base_currency})`
    };

    for (const [field, label] of Object.entries({...costing_labels, ...actuals_labels})) {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "label", label);
        }
    }

    if (frm.fields_dict.border_clearing_costing_charges) {
        const grid = frm.fields_dict.border_clearing_costing_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }

    if (frm.fields_dict.border_clearing_revenue_charges) {
        const grid = frm.fields_dict.border_clearing_revenue_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    }

    if (frm.fields_dict.border_clearing_cost_charges) {
        const grid = frm.fields_dict.border_clearing_cost_charges.grid;
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }
}

// ==========================================================
// Milestone Toggle & Progress Tracker
// ==========================================================

function toggle_milestone_dates(frm) {
    const pairs = {
        "is_documents_received": "documents_received_date",
        "is_entry_lodged": "entry_lodged_date",
        "is_duty_assessed": "duty_assessed_date",
        "is_duty_paid": "duty_paid_date",
        "is_examination_done": "examination_date",
        "is_release_obtained": "release_date",
        "is_cleared": "cleared_date"
    };

    Object.entries(pairs).forEach(([checkbox, date_field]) => {
        const show = frm.doc[checkbox] === 1;
        frm.set_df_property(date_field, "hidden", !show);
        frm.refresh_field(date_field);
    });
}

function render_progress_dial_and_theme_chips(frm) {
    if (!frm.fields_dict.milestone_tracker) return;

    const milestones = [
        { label: "Documents Received", field: "is_documents_received" },
        { label: "Entry Lodged", field: "is_entry_lodged" },
        { label: "Duty Assessed", field: "is_duty_assessed" },
        { label: "Duty Paid", field: "is_duty_paid" },
        { label: "Release Obtained", field: "is_release_obtained" },
        { label: "Cleared", field: "is_cleared" }
    ];

    // Conditionally add examination if required
    if (frm.doc.is_examination_required) {
        milestones.splice(4, 0, { label: "Examination Done", field: "is_examination_done" });
    }

    const completed = milestones.filter(m => frm.doc[m.field]).length;
    const total = milestones.length;
    const percent = total ? Math.round((completed / total) * 100) : 0;

    let html = `
        <div style="margin-top: 12px; padding: 10px 0;">
            <div style="font-weight: bold; font-size: 14px; margin-bottom: 6px;">
                Milestone Progress
                <span style="color: #fff; background: #146c43; padding: 3px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px;">
                    ${percent}%
                </span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
    `;

    milestones.forEach(m => {
        const done = frm.doc[m.field];
        const bg = done ? '#146c43' : '#dee2e6';
        const color = done ? '#fff' : '#495057';
        const icon = done ? '✔' : '•';

        html += `
            <div style="
                background: ${bg};
                color: ${color};
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s ease;
            " title="${m.label}">
                ${icon} ${m.label}
            </div>
        `;
    });

    html += `</div></div>`;
    frm.fields_dict.milestone_tracker.$wrapper.html(html);
}

// ==========================================================
// INVOICING DIALOG FUNCTIONS
// ==========================================================

function create_sales_invoice_from_charges(frm) {
    const all_rows = frm.doc.border_clearing_revenue_charges || [];
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
                <label style="font-weight: bold; margin-bottom: 5px; display: block;">Customer:</label>
                <select class="customer-filter form-control" style="width: 100%;">
                    <option value="">-- All Customers --</option>
                    ${customers.map(c =>
                        `<option value="${frappe.utils.escape_html(c)}" ${c === customer ? 'selected' : ''}>${frappe.utils.escape_html(c)}</option>`
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
                            <th style="min-width: 200px;">Charge</th>
                            <th style="width: 50px; text-align: center;">PT</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Sell Rate</th>
                            <th style="width: 100px; text-align: right;">Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr${row.is_pass_through ? ' style="background-color: #fff3cd;"' : ''}>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${frappe.utils.escape_html(row.name || '')}" ${!row.name ? 'disabled title="Save the Job to invoice this newly added row"' : ''}>
                                </td>
                                <td>${frappe.utils.escape_html(row.customer || '')}</td>
                                <td>${frappe.utils.escape_html(row.charge || '')}</td>
                                <td style="text-align: center;">${row.is_pass_through ? '✔' : ''}</td>
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
            <div style="margin-top: 8px; font-size: 12px; color: #856404;">
                <strong>PT</strong> = Pass-Through (highlighted rows use clearing account)
            </div>
        `;

        dialog.fields_dict.charge_rows_html.$wrapper.html(customer_filter + table);

        dialog.$wrapper.find('.customer-filter').off('change').on('change', function() {
            selected_customer = this.value;
            render_dialog_ui(dialog, selected_customer);
        });

        dialog.$wrapper.find('.select-all-charges').off('change').on('change', function() {
            dialog.$wrapper.find('.charge-row-check').prop('checked', this.checked);
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
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'charge_rows_html',
            options: ''
        }],
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
                method: 'freightmas.border_clearing_service.doctype.border_clearing_job.border_clearing_job.create_sales_invoice_with_rows',
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
                        dialog.hide();
                        const target = `/app/sales-invoice/${encodeURIComponent(r.message)}`;
                        window.location.assign(target);
                    }
                }
            });
        }
    });

    dialog.show();
    render_dialog_ui(dialog, selected_customer);
}

function create_purchase_invoice_from_charges(frm) {
    const all_rows = frm.doc.border_clearing_cost_charges || [];
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
                <label style="font-weight: bold; margin-bottom: 5px; display: block;">Supplier:</label>
                <select class="supplier-filter form-control" style="width: 100%;">
                    <option value="">-- All Suppliers --</option>
                    ${suppliers.map(s =>
                        `<option value="${frappe.utils.escape_html(s)}" ${s === supplier ? 'selected' : ''}>${frappe.utils.escape_html(s)}</option>`
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
                            <th style="width: 50px; text-align: center;">PT</th>
                            <th style="width: 80px; text-align: right;">Qty</th>
                            <th style="width: 100px; text-align: right;">Buy Rate</th>
                            <th style="width: 100px; text-align: right;">Cost</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr${row.is_pass_through ? ' style="background-color: #fff3cd;"' : ''}>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="charge-row-check" data-row-name="${frappe.utils.escape_html(row.name || '')}" ${!row.name ? 'disabled title="Save the Job to invoice this newly added row"' : ''}>
                                </td>
                                <td>${frappe.utils.escape_html(row.supplier || '')}</td>
                                <td>${frappe.utils.escape_html(row.charge || '')}</td>
                                <td style="text-align: center;">${row.is_pass_through ? '✔' : ''}</td>
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
            <div style="margin-top: 8px; font-size: 12px; color: #856404;">
                <strong>PT</strong> = Pass-Through (highlighted rows use clearing account)
            </div>
        `;

        dialog.fields_dict.charge_rows_html.$wrapper.html(supplier_filter + table);

        dialog.$wrapper.find('.supplier-filter').off('change').on('change', function() {
            selected_supplier = this.value;
            render_dialog_ui(dialog, selected_supplier);
        });

        dialog.$wrapper.find('.select-all-charges').off('change').on('change', function() {
            dialog.$wrapper.find('.charge-row-check').prop('checked', this.checked);
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
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'charge_rows_html',
            options: ''
        }],
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
                method: 'freightmas.border_clearing_service.doctype.border_clearing_job.border_clearing_job.create_purchase_invoice_with_rows',
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
                        dialog.hide();
                        frappe.set_route("Form", "Purchase Invoice", r.message);
                    }
                }
            });
        }
    });

    dialog.show();
    render_dialog_ui(dialog, selected_supplier);
}

// ==========================================================
// LOAD CHARGES FROM TEMPLATE
// ==========================================================

function open_charges_template_dialog(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Clearing Charges Template',
            fields: ['name', 'shipping_line', 'container_type', 'direction'],
            limit_page_length: 50,
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                let template_options = r.message.map(tpl =>
                    `${tpl.name} (${tpl.shipping_line || ''} / ${tpl.container_type || ''} / ${tpl.direction || ''})`
                );
                let template_names = r.message.map(tpl => tpl.name);

                let d = new frappe.ui.Dialog({
                    title: __('Load Charges from Template'),
                    fields: [
                        {
                            fieldname: 'template',
                            label: 'Template',
                            fieldtype: 'Select',
                            options: template_options,
                            reqd: 1
                        },
                        {
                            fieldname: 'quantity',
                            label: 'Quantity',
                            fieldtype: 'Float',
                            default: 1.0,
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Load Charges',
                    primary_action(values) {
                        let idx = template_options.indexOf(values.template);
                        if (idx >= 0) {
                            let template_name = template_names[idx];
                            let quantity = values.quantity || 1;
                            fetch_and_append_template_charges(frm, template_name, quantity);
                        }
                        d.hide();
                    }
                });
                d.show();
            } else {
                frappe.msgprint(__('No templates found.'));
            }
        }
    });
}

function fetch_and_append_template_charges(frm, template_name, quantity) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Clearing Charges Template',
            name: template_name
        },
        callback: function (r) {
            if (r.message && r.message.clearing_charges_template_item) {
                let items = r.message.clearing_charges_template_item;
                let parent_customer = frm.doc.customer;
                let existing_charges = (frm.doc.border_clearing_costing_charges || []).map(row => row.charge);

                let added_count = 0;
                items.forEach(row => {
                    if (!existing_charges.includes(row.charge)) {
                        let child = frm.add_child('border_clearing_costing_charges', {
                            charge: row.charge,
                            sell_rate: row.sell_rate,
                            buy_rate: row.buy_rate,
                            supplier: row.supplier,
                            customer: parent_customer,
                            qty: quantity
                        });
                        child.revenue_amount = (quantity || 0) * (row.sell_rate || 0);
                        child.cost_amount = (quantity || 0) * (row.buy_rate || 0);
                        child.margin_amount = child.revenue_amount - child.cost_amount;
                        child.margin_percentage = child.revenue_amount > 0 ? (child.margin_amount / child.revenue_amount) * 100 : 0;
                        added_count += 1;
                    }
                });

                frm.refresh_field('border_clearing_costing_charges');
                calculate_costing_totals(frm);

                if (added_count === 0) {
                    frappe.msgprint(__('All template charges already exist in the costing table. No new charges added.'));
                } else {
                    frappe.msgprint(__(`${added_count} charge(s) loaded from template into Job Costing table.`));
                }
            }
        }
    });
}

// ==========================================================
// REVENUE RECOGNITION DATE DIALOG
// ==========================================================

function show_recognition_date_dialog(frm) {
    frappe.call({
        method: "freightmas.utils.revenue_recognition.get_earliest_invoice_date",
        args: {
            job_doctype: "Border Clearing Job",
            job_name: frm.doc.name
        },
        callback: function(r) {
            const invoice_info = r.message || {};
            const earliest_date = invoice_info.earliest_date;
            const invoice_count = invoice_info.invoice_count || 0;

            let fields = [
                {
                    fieldname: "revenue_recognition_date",
                    label: "Revenue Recognition Date",
                    fieldtype: "Date",
                    reqd: 1,
                    default: earliest_date || frappe.datetime.nowdate()
                }
            ];

            if (invoice_count > 0 && earliest_date) {
                fields.unshift({
                    fieldname: "info",
                    fieldtype: "HTML",
                    options: `<div class="alert alert-info">
                        <strong>Earliest Invoice Date:</strong> ${earliest_date}<br>
                        <strong>Number of Sales Invoices:</strong> ${invoice_count}
                    </div>`
                });
            }

            let d = new frappe.ui.Dialog({
                title: __('Set Revenue Recognition Date'),
                fields: fields,
                primary_action_label: __('Set Date'),
                primary_action(values) {
                    frm.set_value('revenue_recognised_on', values.revenue_recognition_date);
                    frm.dirty();
                    frm.save().then(() => {
                        frappe.show_alert({
                            message: __('Revenue Recognition Date set to {0}', [values.revenue_recognition_date]),
                            indicator: 'green'
                        });
                    });
                    d.hide();
                }
            });
            d.show();
        }
    });
}

// ==========================================================
// UTILITY HELPERS
// ==========================================================

function set_main_value_safe(frm, field, value) {
    if (frm.fields_dict[field]) {
        frm.set_value(field, value);
    }
}
