// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// ==========================================================
// Clearing Job - Client Script
// Handles currency logic, charge calculations (3-table pattern),
// invoicing dialogs, milestone tracking, and cargo count summary
// ==========================================================

frappe.ui.form.on('Clearing Job', {
    refresh: function(frm) {
        toggle_directional_fields(frm);
        toggle_bl_fields(frm);
        toggle_milestone_dates(frm);
        render_progress_dial_and_theme_chips(frm);
        toggle_base_fields(frm);
        update_currency_labels(frm);
        update_cargo_count(frm);
        toggle_costing_table_lock(frm);

        // Custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Create Sales Invoice'), function() {
                create_sales_invoice_from_charges(frm);
            }, __('Create'));

            frm.add_custom_button(__('Create Purchase Invoice'), function() {
                create_purchase_invoice_from_charges(frm);
            }, __('Create'));

            // View > Cost Sheet button
            frm.add_custom_button(__('Cost Sheet'), function() {
                window.open(
                    `/printview?doctype=Clearing%20Job&name=${frm.doc.name}&format=Clearing%20Job%20Cost%20Sheet&no_letterhead=1`,
                    '_blank'
                );
            }, __('View'));
        }
    },

    // Revenue Recognition - Set Date Button
    set_rr_date: function(frm) {
        show_recognition_date_dialog(frm);
    },

    shipping_line: function(frm) {
        if (frm.doc.shipping_line) {
            frappe.db.get_doc('Shipping Line', frm.doc.shipping_line)
                .then(doc => {
                    if (doc.free_days_import && frm.doc.direction === "Import") {
                        set_main_value_safe(frm, 'dnd_free_days', doc.free_days_import);
                        set_main_value_safe(frm, 'port_free_days', doc.free_days_import);
                    }
                    if (doc.free_days_export && frm.doc.direction === "Export") {
                        set_main_value_safe(frm, 'dnd_free_days', doc.free_days_export);
                        set_main_value_safe(frm, 'port_free_days', doc.free_days_export);
                    }
                });
        }
    },

    direction: function(frm) {
        if (frm.doc.shipping_line) {
            frappe.ui.form.trigger('Clearing Job', 'shipping_line', frm);
        }
        toggle_directional_fields(frm);
    },

    is_bl_received: function(frm) {
        toggle_bl_fields(frm);
    },

    is_bl_confirmed: function(frm) {
        toggle_bl_fields(frm);
    },

    // Import Milestones
    is_discharged_from_vessel: toggle_milestone_dates,
    is_vessel_arrived_at_port: toggle_milestone_dates,
    is_discharged_from_port: toggle_milestone_dates,
    is_do_requested: toggle_milestone_dates,
    is_do_received: toggle_milestone_dates,
    is_port_release_confirmed: toggle_milestone_dates,
    is_sl_invoice_received: toggle_milestone_dates,
    is_sl_invoice_paid: toggle_milestone_dates,

    // Export Milestones
    is_booking_confirmed: toggle_milestone_dates,
    is_clearing_for_shipment_done: toggle_milestone_dates,
    is_loaded_on_vessel: toggle_milestone_dates,
    is_vessel_sailed: toggle_milestone_dates,

    validate: function(frm) {
        let missing_fields = [];

        // Helper to validate checkbox-date pairs
        const check_date = (checkbox, date_field, label) => {
            if (frm.doc[checkbox] && !frm.doc[date_field]) {
                missing_fields.push(label);
            }
        };

        if (frm.doc.direction === "Import") {
            check_date("is_discharged_from_vessel", "discharge_date", "Date Discharged from Vessel");
            check_date("is_vessel_arrived_at_port", "vessel_arrived_date", "Vessel Arrived Date");
            check_date("is_discharged_from_port", "date_discharged_from_port", "Date Discharged from Port");
            check_date("is_do_requested", "do_requested_date", "DO Requested Date");
            check_date("is_do_received", "do_received_date", "DO Received Date");
            check_date("is_port_release_confirmed", "port_release_confirmed_date", "Port Release Confirmed Date");
            check_date("is_sl_invoice_received", "sl_invoice_received_date", "SL Invoice Received Date");
            check_date("is_sl_invoice_paid", "sl_invoice_payment_date", "SL Invoice Payment Date");
        }

        if (frm.doc.direction === "Export") {
            check_date("is_booking_confirmed", "booking_confirmation_date", "Booking Confirmation Date");
            check_date("is_clearing_for_shipment_done", "shipment_cleared_date", "Shipment Cleared Date");
            check_date("is_loaded_on_vessel", "loaded_on_vessel_date", "Loaded on Vessel Date");
            check_date("is_vessel_sailed", "vessel_sailed_date", "Vessel Sailed Date");
        }

        // BL Validation
        if (frm.doc.is_bl_received) {
            if (!frm.doc.bl_type) missing_fields.push("BL Type");
            if (!frm.doc.bl_received_date) missing_fields.push("BL Received Date");

            if (frm.doc.is_bl_confirmed && !frm.doc.bl_confirmed_date) {
                missing_fields.push("BL Confirmed Date");
            }
        }

        if (missing_fields.length > 0) {
            frappe.throw(__("Please fill the following required fields:<br><ul><li>{0}</li></ul>", [missing_fields.join("</li><li>")]));
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
        const tracking = frm.doc.clearing_tracking;
        if (tracking && tracking.length > 0) {
            const last = tracking[tracking.length - 1];
            set_main_value_safe(frm, 'current_comment', last.comment);
            set_main_value_safe(frm, 'last_updated_on', last.updated_on);
            set_main_value_safe(frm, 'last_updated_by', last.updated_by);
        }
    },

    // Template and Quotation loading buttons
    load_charges_from_template(frm) {
        open_charges_template_dialog(frm);
    },

    fetch_from_quotation(frm) {
        open_fetch_charges_from_quotation_dialog_clearing(frm);
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
    "is_vessel_arrived_at_port", "is_discharged_from_vessel", "is_discharged_from_port",
    "is_do_requested", "is_do_received", "is_port_release_confirmed",
    "is_sl_invoice_received", "is_sl_invoice_paid",
    "is_booking_confirmed", "is_clearing_for_shipment_done", "is_loaded_on_vessel", "is_vessel_sailed"
].forEach(field => {
    frappe.ui.form.on('Clearing Job', {
        [`${field}`]: function(frm) {
            render_progress_dial_and_theme_chips(frm);
        }
    });
});

// ==========================================================
// CLEARING COSTING CHARGES (Quoted/Planned)
// ==========================================================
frappe.ui.form.on('Clearing Costing Charges', {
    clearing_costing_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_costing_totals(frm);
    },

    clearing_costing_charges_remove: function(frm) {
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

// ==========================================================
// CLEARING REVENUE CHARGES (Working Revenue)
// ==========================================================
frappe.ui.form.on('Clearing Revenue Charges', {
    clearing_revenue_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_actual_totals(frm);
    },

    clearing_revenue_charges_remove: function(frm) {
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
        const grid_row = frm.fields_dict.clearing_revenue_charges.grid.grid_rows_by_docname[cdn];
        if (row?.sales_invoice_reference) {
            grid_row.columns.forEach(col => {
                if (col.df.fieldname !== 'sales_invoice_reference') {
                    col.df.read_only = 1;
                }
            });
            grid_row.refresh();
        }
    },

    before_clearing_revenue_charges_remove(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row?.sales_invoice_reference) {
            frappe.throw(__('Cannot delete a revenue charge linked to Sales Invoice {0}.', [row.sales_invoice_reference]));
        }
    }
});

// ==========================================================
// CLEARING COST CHARGES (Working Cost)
// ==========================================================
frappe.ui.form.on('Clearing Cost Charges', {
    clearing_cost_charges_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.qty) {
            frappe.model.set_value(cdt, cdn, 'qty', 1);
        }
        calculate_actual_totals(frm);
    },

    clearing_cost_charges_remove: function(frm) {
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
        const grid_row = frm.fields_dict.clearing_cost_charges.grid.grid_rows_by_docname[cdn];
        if (row?.purchase_invoice_reference) {
            grid_row.columns.forEach(col => {
                if (col.df.fieldname !== 'purchase_invoice_reference') {
                    col.df.read_only = 1;
                }
            });
            grid_row.refresh();
        }
    },

    before_clearing_cost_charges_remove(frm, cdt, cdn) {
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

    $.each(frm.doc.clearing_costing_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
        total_cost += flt(row.cost_amount);
    });

    let total_profit = flt(total_revenue - total_cost, 2);
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? flt((total_profit / total_revenue * 100), 2) : 0;

    set_main_value_safe(frm, 'total_quoted_revenue', flt(total_revenue, 2));
    set_main_value_safe(frm, 'total_quoted_cost', flt(total_cost, 2));
    set_main_value_safe(frm, 'total_quoted_margin', total_profit);
    set_main_value_safe(frm, 'quoted_margin_percent', profit_margin_percent);

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

    $.each(frm.doc.clearing_revenue_charges || [], function(i, row) {
        total_revenue += flt(row.revenue_amount);
    });

    $.each(frm.doc.clearing_cost_charges || [], function(i, row) {
        total_cost += flt(row.cost_amount);
    });

    let total_profit = total_revenue - total_cost;
    let rate = flt(frm.doc.conversion_rate) || 1.0;
    let profit_margin_percent = total_revenue > 0 ? (total_profit / total_revenue * 100) : 0;

    set_main_value_safe(frm, 'total_working_revenue', total_revenue);
    set_main_value_safe(frm, 'total_working_cost', total_cost);
    set_main_value_safe(frm, 'total_working_profit', total_profit);
    set_main_value_safe(frm, 'profit_margin_percent', profit_margin_percent);

    set_main_value_safe(frm, 'total_working_revenue_base', total_revenue * rate);
    set_main_value_safe(frm, 'total_working_base', total_cost * rate);
    set_main_value_safe(frm, 'total_working_profit_base', total_profit * rate);

    frm.refresh_fields();
}

// ==========================================================
// COSTING TABLE LOCK (prevent editing once job leaves Draft)
// ==========================================================

function toggle_costing_table_lock(frm) {
    const fieldname = 'clearing_costing_charges';
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
                        if (col && col.df) {
                            col.df.read_only = 1;
                        }
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
// Show/Hide Base Currency Fields
// ==========================================================

function toggle_base_fields(frm) {
    const show = frm.doc.currency !== frm.doc.base_currency;

    // Costing section
    frm.toggle_display('total_quoted_revenue_base', show);
    frm.toggle_display('total_quoted_cost_base', show);
    frm.toggle_display('total_quoted_profit_base', show);

    // Actuals section
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

    // Costing labels
    const costing_labels = {
        total_quoted_revenue: `Total Quoted Revenue (${currency})`,
        total_quoted_cost: `Total Quoted Cost (${currency})`,
        total_quoted_margin: `Total Quoted Profit (${currency})`,
        total_quoted_revenue_base: `Total Quoted Revenue (${base_currency})`,
        total_quoted_cost_base: `Total Quoted Cost (${base_currency})`,
        total_quoted_profit_base: `Total Quoted Profit (${base_currency})`
    };

    // Actuals labels
    const actuals_labels = {
        total_working_revenue: `Working Revenue (${currency})`,
        total_working_cost: `Working Cost (${currency})`,
        total_working_profit: `Total Working Margin (${currency})`,
        total_working_revenue_base: `Total Working Revenue (${base_currency})`,
        total_working_base: `Total Working Cost (${base_currency})`,
        total_working_profit_base: `Total Working Margin (${base_currency})`
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
    if (frm.fields_dict.clearing_costing_charges) {
        const grid = frm.fields_dict.clearing_costing_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }

    // Update revenue charges child table labels
    if (frm.fields_dict.clearing_revenue_charges) {
        const grid = frm.fields_dict.clearing_revenue_charges.grid;
        grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
        grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    }

    // Update cost charges child table labels
    if (frm.fields_dict.clearing_cost_charges) {
        const grid = frm.fields_dict.clearing_cost_charges.grid;
        grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
        grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
    }
}

// ==========================================================
// Helper Functions - Directional Fields, BL, Milestones
// ==========================================================

function toggle_directional_fields(frm) {
    const is_import = frm.doc.direction === "Import";
    const is_export = frm.doc.direction === "Export";

    // Import-specific fields
    const import_checkboxes = [
        "is_discharged_from_vessel", "is_vessel_arrived_at_port", "is_discharged_from_port", "is_do_requested",
        "is_do_received", "is_port_release_confirmed", "is_sl_invoice_received", "is_sl_invoice_paid"
    ];
    const import_dates = [
        "discharge_date", "vessel_arrived_date", "date_discharged_from_port", "do_requested_date",
        "do_received_date", "port_release_confirmed_date", "sl_invoice_received_date", "sl_invoice_payment_date"
    ];

    // Export-specific fields
    const export_checkboxes = [
        "is_booking_confirmed", "is_clearing_for_shipment_done", "is_loaded_on_vessel", "is_vessel_sailed"
    ];
    const export_dates = [
        "booking_confirmation_date", "shipment_cleared_date", "loaded_on_vessel_date", "vessel_sailed_date"
    ];

    [...import_checkboxes, ...import_dates].forEach(field => {
        frm.set_df_property(field, "hidden", !is_import);
    });

    [...export_checkboxes, ...export_dates].forEach(field => {
        frm.set_df_property(field, "hidden", !is_export);
    });

    frm.refresh_fields();
}

function toggle_bl_fields(frm) {
    frm.set_df_property("bl_type", "hidden", !frm.doc.is_bl_received);
    frm.set_df_property("bl_received_date", "hidden", !frm.doc.is_bl_received);
    frm.set_df_property("is_bl_confirmed", "hidden", !frm.doc.is_bl_received);
    frm.set_df_property("bl_confirmed_date", "hidden", !(frm.doc.is_bl_received && frm.doc.is_bl_confirmed));
    frm.refresh_fields();
}

function toggle_milestone_dates(frm) {
    const pairs = {
        "is_discharged_from_vessel": "discharge_date",
        "is_vessel_arrived_at_port": "vessel_arrived_date",
        "is_discharged_from_port": "date_discharged_from_port",
        "is_do_requested": "do_requested_date",
        "is_do_received": "do_received_date",
        "is_port_release_confirmed": "port_release_confirmed_date",
        "is_sl_invoice_received": "sl_invoice_received_date",
        "is_sl_invoice_paid": "sl_invoice_payment_date",
        "is_booking_confirmed": "booking_confirmation_date",
        "is_clearing_for_shipment_done": "shipment_cleared_date",
        "is_loaded_on_vessel": "loaded_on_vessel_date",
        "is_vessel_sailed": "vessel_sailed_date"
    };

    Object.entries(pairs).forEach(([checkbox, date_field]) => {
        const show = frm.doc[checkbox] === 1;
        frm.set_df_property(date_field, "hidden", !show);
        frm.refresh_field(date_field);
    });
}

function render_progress_dial_and_theme_chips(frm) {
    if (!frm.fields_dict.milestone_tracker) return;

    const import_milestones = [
        { label: "Vessel Arrived", field: "is_vessel_arrived_at_port" },
        { label: "Discharged from Vessel", field: "is_discharged_from_vessel" },
        { label: "SL Invoice Received", field: "is_sl_invoice_received" },
        { label: "SL Invoice Paid", field: "is_sl_invoice_paid" },
        { label: "DO Requested", field: "is_do_requested" },
        { label: "DO Received", field: "is_do_received" },
        { label: "Port Release Confirmed", field: "is_port_release_confirmed" },
        { label: "Discharged from Port", field: "is_discharged_from_port" }
    ];

    const export_milestones = [
        { label: "Booking Confirmed", field: "is_booking_confirmed" },
        { label: "Shipment Cleared", field: "is_clearing_for_shipment_done" },
        { label: "Loaded Vessel", field: "is_loaded_on_vessel" },
        { label: "Vessel Sailed", field: "is_vessel_sailed" }
    ];

    const direction = frm.doc.direction;
    const milestones = direction === "Import" ? import_milestones : export_milestones;
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
    const all_rows = frm.doc.clearing_revenue_charges || [];
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
                            <th style="min-width: 200px;">Charge</th>
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
                method: 'freightmas.clearing_service.doctype.clearing_job.clearing_job.create_sales_invoice_with_rows',
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
                        frappe.set_route("Form", "Sales Invoice", r.message);
                    }
                }
            });
        }
    });

    dialog.show();
    render_dialog_ui(dialog, selected_customer);
}

function create_purchase_invoice_from_charges(frm) {
    const all_rows = frm.doc.clearing_cost_charges || [];
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
                method: 'freightmas.clearing_service.doctype.clearing_job.clearing_job.create_purchase_invoice_with_rows',
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
// LOAD CHARGES FROM TEMPLATE (into costing table)
// ==========================================================

function open_charges_template_dialog(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Clearing Charges Template',
            filters: {
                direction: frm.doc.direction,
                shipping_line: frm.doc.shipping_line
            },
            fields: ['name', 'shipping_line', 'container_type', 'direction'],
            limit_page_length: 50,
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                let template_options = r.message.map(tpl =>
                    `${tpl.name} (${tpl.shipping_line || ''} / ${tpl.container_type || ''} / ${tpl.direction})`
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
                frappe.msgprint(__('No matching templates found for this direction and shipping line.'));
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
                let existing_charges = (frm.doc.clearing_costing_charges || []).map(row => row.charge);

                let added_count = 0;
                items.forEach(row => {
                    if (!existing_charges.includes(row.charge)) {
                        let child = frm.add_child('clearing_costing_charges', {
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

                frm.refresh_field('clearing_costing_charges');
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
// FETCH CHARGES FROM QUOTATION (into costing table)
// ==========================================================

function open_fetch_charges_from_quotation_dialog_clearing(frm) {
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
                ['job_type', '=', "Clearing"],
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
                            fetch_and_append_quotation_charges_clearing(frm, quotation_name);
                        }
                        d.hide();
                    }
                });
                d.show();
            } else {
                frappe.msgprint(__('No valid Clearing Quotations found for this customer.'));
            }
        }
    });
}

function fetch_and_append_quotation_charges_clearing(frm, quotation_name) {
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
                let existing_charges = (frm.doc.clearing_costing_charges || []).map(row => row.charge);

                let added_count = 0;
                items.forEach(item => {
                    if (!existing_charges.includes(item.item_code)) {
                        let child = frm.add_child('clearing_costing_charges', {
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
                        child.margin_percentage = child.revenue_amount > 0 ? (child.margin_amount / child.revenue_amount) * 100 : 0;
                        added_count += 1;
                    }
                });

                frm.refresh_field('clearing_costing_charges');
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

// ==========================================================
// CARGO PACKAGE COUNT SUMMARY LOGIC
// ==========================================================

function update_cargo_count(frm) {
    let table = frm.doc.cargo_package_details || [];
    let container_counts = {};
    let package_count = 0;

    table.forEach(row => {
        if (row.cargo_type && row.cargo_type.toLowerCase() === "containerised") {
            let ctype = row.container_type || "Unknown Type";
            container_counts[ctype] = (container_counts[ctype] || 0) + 1;
        } else {
            package_count += row.cargo_quantity ? row.cargo_quantity : 1;
        }
    });

    let summary = [];
    Object.keys(container_counts).forEach(type => {
        summary.push(`${container_counts[type]} x ${type}`);
    });
    if (package_count > 0) {
        summary.push(`${package_count} x PKG${package_count > 1 ? "s" : ""}`);
    }
    set_main_value_safe(frm, "cargo_count", summary.join(", "));
}

// Child table triggers for cargo count
frappe.ui.form.on('Cargo Package Details', {
    cargo_type: update_cargo_count,
    container_type: update_cargo_count,
    cargo_quantity: update_cargo_count,
    cargo_package_details_add: function(frm) { update_cargo_count(frm); },
    cargo_package_details_remove: function(frm) { update_cargo_count(frm); }
});

// ==========================================================
// DND AND STORAGE DATE LOGIC
// ==========================================================

function update_dnd_and_storage_dates(frm) {
    const discharge_date = frm.doc.discharge_date;
    const is_discharged_from_vessel = frm.doc.is_discharged_from_vessel;
    const dnd_days = parseInt(frm.doc.dnd_free_days) || 0;
    const port_days = parseInt(frm.doc.port_free_days) || 0;

    if (discharge_date && is_discharged_from_vessel) {
        const dnd_start = frappe.datetime.add_days(discharge_date, dnd_days + 1);
        const storage_start = frappe.datetime.add_days(discharge_date, port_days + 1);

        set_main_value_safe(frm, "dnd_start_date", dnd_start);
        set_main_value_safe(frm, "storage_start_date", storage_start);
    } else {
        set_main_value_safe(frm, "dnd_start_date", null);
        set_main_value_safe(frm, "storage_start_date", null);
        if (!is_discharged_from_vessel && discharge_date) {
            set_main_value_safe(frm, "discharge_date", null);
        }
    }
}

frappe.ui.form.on('Clearing Job', {
    discharge_date: update_dnd_and_storage_dates,
    dnd_free_days: update_dnd_and_storage_dates,
    port_free_days: update_dnd_and_storage_dates,
    is_discharged_from_vessel: update_dnd_and_storage_dates
});

// ==========================================================
// Cargo Package Details - Conditional Logic
// ==========================================================

frappe.ui.form.on('Cargo Package Details', {
    is_empty_picked: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_empty_picked) {
            set_child_value_safe(frm, cdt, cdn, 'is_gated_in_port', 0);
            set_child_value_safe(frm, cdt, cdn, 'is_loaded_on_vessel', 0);
            set_child_value_safe(frm, cdt, cdn, 'pick_up_empty_date', null);
            set_child_value_safe(frm, cdt, cdn, 'gate_in_full_date', null);
            set_child_value_safe(frm, cdt, cdn, 'loaded_on_vessel_date', null);
        }
    },
    is_gated_in_port: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_gated_in_port && !row.is_empty_picked) {
            frappe.msgprint(__('Please tick "Is Empty Picked" before "Is Gated In Port"'));
            set_child_value_safe(frm, cdt, cdn, 'is_gated_in_port', 0);
            return;
        }
        if (!row.is_gated_in_port) {
            set_child_value_safe(frm, cdt, cdn, 'is_loaded_on_vessel', 0);
            set_child_value_safe(frm, cdt, cdn, 'gate_in_full_date', null);
            set_child_value_safe(frm, cdt, cdn, 'loaded_on_vessel_date', null);
        }
    },
    is_loaded_on_vessel: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_loaded_on_vessel && (!row.is_empty_picked || !row.is_gated_in_port)) {
            frappe.msgprint(__('Please tick prior steps before "Is Loaded On Vessel"'));
            set_child_value_safe(frm, cdt, cdn, 'is_loaded_on_vessel', 0);
            return;
        }
        if (!row.is_loaded_on_vessel) {
            set_child_value_safe(frm, cdt, cdn, 'loaded_on_vessel_date', null);
        }
    },
    pick_up_empty_date: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_empty_picked && row.pick_up_empty_date) {
            set_child_value_safe(frm, cdt, cdn, 'pick_up_empty_date', null);
        }
    },
    gate_in_full_date: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_gated_in_port && row.gate_in_full_date) {
            set_child_value_safe(frm, cdt, cdn, 'gate_in_full_date', null);
        }
    },
    loaded_on_vessel_date: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_loaded_on_vessel && row.loaded_on_vessel_date) {
            set_child_value_safe(frm, cdt, cdn, 'loaded_on_vessel_date', null);
        }
    }
});

// ==========================================================
// REVENUE RECOGNITION DATE DIALOG
// ==========================================================

function show_recognition_date_dialog(frm) {
    frappe.call({
        method: "freightmas.utils.revenue_recognition.get_earliest_invoice_date",
        args: {
            job_doctype: "Clearing Job",
            job_name: frm.doc.name
        },
        callback: function(r) {
            const invoice_info = r.message || {};
            const earliest_date = invoice_info.earliest_date;
            const invoice_count = invoice_info.invoice_count || 0;

            let info_html = `<p class="text-muted">
                ${__('Set the date when revenue should be recognized for this job.')}
                <br><br>
                ${__('This is typically the job completion date. Once set, you can submit the job to recognize revenue.')}
            </p>`;

            if (invoice_count > 0 && earliest_date) {
                info_html += `<p class="text-warning">
                    <strong>${__('Note:')}</strong> ${__('There are {0} submitted invoice(s) linked to this job. The earliest invoice date is {1}. The recognition date cannot be earlier than this.', [invoice_count, frappe.datetime.str_to_user(earliest_date)])}
                </p>`;
            } else {
                info_html += `<p class="text-info">
                    ${__('No submitted invoices found yet. Revenue will be recognized when invoices are submitted after job completion.')}
                </p>`;
            }

            const dialog = new frappe.ui.Dialog({
                title: __('Set Revenue Recognition Date'),
                fields: [
                    {
                        fieldname: 'info',
                        fieldtype: 'HTML',
                        options: info_html
                    },
                    {
                        fieldname: 'revenue_recognised_on',
                        fieldtype: 'Date',
                        label: __('Revenue Recognition Date'),
                        reqd: 1,
                        default: frm.doc.completed_on || frappe.datetime.get_today()
                    }
                ],
                primary_action_label: __('Set Date'),
                primary_action: function(values) {
                    if (earliest_date && values.revenue_recognised_on < earliest_date) {
                        frappe.msgprint({
                            title: __('Invalid Date'),
                            indicator: 'red',
                            message: __('Revenue Recognition Date cannot be earlier than the earliest invoice date ({0}).', [frappe.datetime.str_to_user(earliest_date)])
                        });
                        return;
                    }

                    frm.set_value('revenue_recognised_on', values.revenue_recognised_on);
                    frm.save().then(() => {
                        dialog.hide();
                        frappe.show_alert({
                            message: __('Revenue Recognition Date set to {0}. You can now submit the job.',
                                [frappe.datetime.str_to_user(values.revenue_recognised_on)]),
                            indicator: 'green'
                        }, 7);
                    });
                }
            });
            dialog.show();
        }
    });
}

// ==========================================================
// Safe Value Setters
// ==========================================================

function set_main_value_safe(frm, fieldname, value) {
    const current = frm.doc[fieldname];

    const normalize = v => {
        if (v === undefined || v === null) return "";
        if (typeof v === "number") return v.toString();
        if (typeof v === "boolean") return v ? "1" : "0";
        if (v instanceof Date) return v.toISOString();
        if (typeof v === "object") {
            try { return JSON.stringify(v); } catch (e) { return String(v); }
        }
        return String(v);
    };

    if (normalize(current) === normalize(value)) return;
    frm.set_value(fieldname, value);
}

function set_child_value_safe(frm, cdt, cdn, fieldname, value) {
    const row = locals[cdt][cdn];
    if (row && row[fieldname] !== value) {
        frappe.model.set_value(cdt, cdn, fieldname, value);
    }
}

// Strip HTML tags from a description string
function strip_html_tags(html) {
    let tmp = document.createElement("DIV");
    tmp.innerHTML = html || "";
    return tmp.textContent || tmp.innerText || "";
}
