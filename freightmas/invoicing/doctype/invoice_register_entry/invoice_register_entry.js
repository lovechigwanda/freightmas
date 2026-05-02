// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Register Entry', {
    refresh(frm) {
        // ========================================
        // DYNAMIC FIELD VISIBILITY
        // ========================================
        toggle_entry_type_fields(frm);

        // ========================================
        // JOB SEARCH BY BL / CUSTOMER REFERENCE
        // ========================================
        setup_job_search_query(frm);

        // ========================================
        // CHARGE TABLE LABELS
        // ========================================
        update_charge_table_labels(frm);

        // ========================================
        // STATUS TRANSITION BUTTONS
        // ========================================
        if (!frm.is_new() && frm.doc.status) {
            add_status_transition_buttons(frm);
        }

        // ========================================
        // COLOUR-CODED STATUS INDICATOR
        // ========================================
        set_status_indicator(frm);
    },

    entry_type(frm) {
        toggle_entry_type_fields(frm);

        // Auto-set party_type
        if (frm.doc.entry_type === 'Sales') {
            frm.set_value('party_type', 'Customer');
        } else if (frm.doc.entry_type === 'Purchase') {
            frm.set_value('party_type', 'Supplier');
        }
    },

    amount(frm) {
        calculate_base_amount(frm);
    },

    conversion_rate(frm) {
        calculate_base_amount(frm);
    },

    job_name(frm) {
        // When job is selected, auto-fetch party for Sales entries
        if (frm.doc.entry_type === 'Sales' && frm.doc.job_name && frm.doc.job_doctype) {
            frappe.db.get_value(frm.doc.job_doctype, frm.doc.job_name, 'customer', (r) => {
                if (r && r.customer) {
                    frm.set_value('party', r.customer);
                }
            });
        }
        // Clear the lookup field after job is selected
        if (frm.doc.job_name && frm.doc.bl_number_lookup) {
            frm.set_value('bl_number_lookup', '');
        }
    },

    bl_number_lookup(frm) {
        // When user types a BL number, search for matching Forwarding Jobs
        const lookup = frm.doc.bl_number_lookup;
        if (!lookup || lookup.length < 3) return;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Forwarding Job',
                filters: {
                    docstatus: ['<', 2]
                },
                or_filters: [
                    ['customer_reference', 'like', '%' + lookup + '%'],
                    ['bl_number', 'like', '%' + lookup + '%']
                ],
                fields: ['name', 'customer', 'customer_reference', 'bl_number'],
                limit_page_length: 10
            },
            callback(r) {
                if (r.message && r.message.length === 1) {
                    // Exact match — auto-populate
                    frm.set_value('job_doctype', 'Forwarding Job');
                    frm.set_value('job_name', r.message[0].name);
                    frappe.show_alert({
                        message: __('Found: {0} ({1})', [r.message[0].name, r.message[0].customer_reference || r.message[0].bl_number]),
                        indicator: 'green'
                    });
                } else if (r.message && r.message.length > 1) {
                    // Multiple matches — show selection dialog
                    show_job_selection_dialog(frm, r.message);
                } else {
                    frappe.show_alert({
                        message: __('No Forwarding Job found for "{0}"', [lookup]),
                        indicator: 'orange'
                    });
                }
            }
        });
    }
});


// ==========================================================
// Toggle field visibility based on entry type
// ==========================================================

function toggle_entry_type_fields(frm) {
    const is_purchase = frm.doc.entry_type === 'Purchase';
    const is_sales = frm.doc.entry_type === 'Sales';

    // Supplier invoice section only for Purchase
    frm.toggle_display('supplier_invoice_section', is_purchase);

    // Party type label
    if (is_sales) {
        frm.set_df_property('party', 'label', 'Customer');
    } else if (is_purchase) {
        frm.set_df_property('party', 'label', 'Supplier');
    }
}


// ==========================================================
// Job search: include customer_reference and bl_number
// ==========================================================

function setup_job_search_query(frm) {
    frm.set_query('job_name', function () {
        return {
            query: 'freightmas.invoicing.doctype.invoice_register_entry.invoice_register_entry.job_query',
            filters: {
                job_doctype: frm.doc.job_doctype || 'Forwarding Job'
            }
        };
    });
}


// ==========================================================
// Show selection dialog when multiple jobs match BL lookup
// ==========================================================

function show_job_selection_dialog(frm, jobs) {
    const fields = [{
        fieldtype: 'HTML',
        fieldname: 'job_list_html'
    }];

    const d = new frappe.ui.Dialog({
        title: __('Multiple Jobs Found'),
        fields: fields,
        size: 'large'
    });

    let html = '<table class="table table-bordered table-hover" style="margin:0">';
    html += '<thead><tr><th>Job ID</th><th>Customer</th><th>Customer Reference</th><th>BL Number</th><th></th></tr></thead><tbody>';
    jobs.forEach(job => {
        html += `<tr>
            <td>${job.name}</td>
            <td>${job.customer || ''}</td>
            <td>${job.customer_reference || ''}</td>
            <td>${job.bl_number || ''}</td>
            <td><button class="btn btn-xs btn-primary select-job" data-job="${job.name}">Select</button></td>
        </tr>`;
    });
    html += '</tbody></table>';

    d.fields_dict.job_list_html.$wrapper.html(html);

    d.$wrapper.on('click', '.select-job', function () {
        const job_name = $(this).data('job');
        frm.set_value('job_doctype', 'Forwarding Job');
        frm.set_value('job_name', job_name);
        d.hide();
    });

    d.show();
}


// ==========================================================
// Compute base amount client-side
// ==========================================================

function calculate_base_amount(frm) {
    const amount = flt(frm.doc.amount);
    const rate = flt(frm.doc.conversion_rate) || 1.0;
    frm.set_value('amount_base', flt(amount * rate, 2));
}


// ==========================================================
// Update charge table labels based on entry type
// ==========================================================

function update_charge_table_labels(frm) {
    if (frm.doc.entry_type === 'Purchase') {
        frm.fields_dict.charge_details.grid.update_docfield_property('rate', 'label', 'Buy Rate');
        frm.fields_dict.charge_details.grid.update_docfield_property('line_party_type', 'default', 'Supplier');
    } else if (frm.doc.entry_type === 'Sales') {
        frm.fields_dict.charge_details.grid.update_docfield_property('rate', 'label', 'Sell Rate');
        frm.fields_dict.charge_details.grid.update_docfield_property('line_party_type', 'default', 'Customer');
    }
}


// ==========================================================
// Calculate charge table totals
// ==========================================================

function calculate_charge_totals(frm) {
    let total = 0;
    (frm.doc.charge_details || []).forEach(row => {
        total += flt(row.line_amount);
    });
    frm.set_value('total_charge_amount', flt(total, 2));
    // Also update the header amount field to match
    frm.set_value('amount', flt(total, 2));
}


// ==========================================================
// Status transition buttons
// ==========================================================

const STATUS_BUTTON_MAP = {
    // Purchase states
    'Received': [
        { label: 'Submit for Approval', target: 'Submitted for Approval', color: 'primary' },
        { label: 'Cancel', target: 'Cancelled', color: 'danger' }
    ],
    'Submitted for Approval': [
        { label: 'Approve & Return for Capture', target: 'Returned for Capture', color: 'primary' },
        { label: 'Query with Supplier', target: 'Query with Supplier', color: 'warning' }
    ],
    'Query with Supplier': [
        { label: 'Mark Ready for Capture', target: 'Ready for Capture', color: 'primary' },
        { label: 'Cancel', target: 'Cancelled', color: 'danger' }
    ],
    'Ready for Capture': [
        { label: 'Mark as Captured', target: 'Captured', color: 'success' }
    ],
    'Returned for Capture': [
        { label: 'Mark as Captured', target: 'Captured', color: 'success' }
    ],

    // Sales states
    'Instruction Received': [
        { label: 'Mark as Drafted', target: 'Drafted', color: 'primary' },
        { label: 'Cancel', target: 'Cancelled', color: 'danger' }
    ],
    'Drafted': [
        { label: 'Issue to Client', target: 'Issued to Client', color: 'success' },
        { label: 'Return to Draft', target: 'Returned to Draft', color: 'warning' }
    ],
    'Returned to Draft': [
        { label: 'Mark as Drafted', target: 'Drafted', color: 'primary' }
    ]
};

// States requiring a comment
const COMMENT_REQUIRED = new Set(['Query with Supplier', 'Returned to Draft', 'Cancelled']);

function add_status_transition_buttons(frm) {
    const buttons = STATUS_BUTTON_MAP[frm.doc.status] || [];

    buttons.forEach(btn => {
        frm.add_custom_button(__(btn.label), function () {
            if (COMMENT_REQUIRED.has(btn.target)) {
                // Show dialog for comment
                show_status_change_dialog(frm, btn.target, btn.label);
            } else {
                // Direct transition
                execute_status_change(frm, btn.target);
            }
        }, __('Actions'));
    });
}

function show_status_change_dialog(frm, target_status, button_label) {
    const d = new frappe.ui.Dialog({
        title: __(button_label),
        fields: [
            {
                label: __('Comment'),
                fieldname: 'comment',
                fieldtype: 'Small Text',
                reqd: 1,
                description: __('Please provide a reason for this status change')
            }
        ],
        primary_action_label: __(button_label),
        primary_action(values) {
            d.hide();
            execute_status_change(frm, target_status, values.comment);
        }
    });
    d.show();
}

function execute_status_change(frm, target_status, comment) {
    frappe.call({
        method: 'change_status',
        doc: frm.doc,
        args: {
            new_status: target_status,
            comment: comment || ''
        },
        freeze: true,
        freeze_message: __('Updating status...'),
        callback(r) {
            if (r && !r.exc) {
                frm.reload_doc();
            }
        }
    });
}


// ==========================================================
// Status indicator colours
// ==========================================================

const STATUS_COLOURS = {
    'Received': 'blue',
    'Submitted for Approval': 'orange',
    'Returned for Capture': 'blue',
    'Query with Supplier': 'red',
    'Ready for Capture': 'blue',
    'Captured': 'green',
    'Instruction Received': 'blue',
    'Drafted': 'orange',
    'Returned to Draft': 'orange',
    'Issued to Client': 'green',
    'Cancelled': 'grey'
};

function set_status_indicator(frm) {
    const colour = STATUS_COLOURS[frm.doc.status];
    if (colour) {
        frm.page.set_indicator(__(frm.doc.status), colour);
    }
}


// ==========================================================
// Charge Details child table events
// ==========================================================

frappe.ui.form.on('Invoice Register Charge', {
    qty(frm, cdt, cdn) {
        calculate_charge_line_amount(frm, cdt, cdn);
    },
    rate(frm, cdt, cdn) {
        calculate_charge_line_amount(frm, cdt, cdn);
    },
    charge_details_remove(frm) {
        calculate_charge_totals(frm);
    }
});

function calculate_charge_line_amount(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    const qty = flt(row.qty) || 1;
    const rate = flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'line_amount', flt(qty * rate, 2));
    calculate_charge_totals(frm);
}
