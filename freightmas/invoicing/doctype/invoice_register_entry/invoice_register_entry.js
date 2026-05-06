// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Register Entry', {
    refresh(frm) {
        toggle_entry_type_fields(frm);
        setup_job_search_query(frm);
        update_charge_table_labels(frm);
        apply_locked_entry_state(frm);

        if (!frm.is_new() && frm.doc.status && !is_invoice_register_locked(frm)) {
            add_status_transition_buttons(frm);
        }

        add_forwarding_working_cost_button(frm);
        set_status_indicator(frm);
    },

    entry_type(frm) {
        toggle_entry_type_fields(frm);
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
        if (frm.doc.entry_type === 'Sales' && frm.doc.job_name && frm.doc.job_doctype) {
            frappe.db.get_value(frm.doc.job_doctype, frm.doc.job_name, 'customer', (r) => {
                if (r && r.customer) {
                    frm.set_value('party', r.customer);
                }
            });
        }
        if (frm.doc.job_name && frm.doc.bl_number_lookup) {
            frm.set_value('bl_number_lookup', '');
        }
    },

    bl_number_lookup(frm) {
        const lookup = frm.doc.bl_number_lookup;
        if (!lookup || lookup.length < 3) return;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Forwarding Job',
                filters: { docstatus: ['<', 2] },
                or_filters: [
                    ['customer_reference', 'like', '%' + lookup + '%'],
                    ['bl_number', 'like', '%' + lookup + '%']
                ],
                fields: ['name', 'customer', 'customer_reference', 'bl_number'],
                limit_page_length: 10
            },
            callback(r) {
                if (r.message && r.message.length === 1) {
                    frm.set_value('job_doctype', 'Forwarding Job');
                    frm.set_value('job_name', r.message[0].name);
                    frappe.show_alert({
                        message: __('Found: {0} ({1})', [r.message[0].name, r.message[0].customer_reference || r.message[0].bl_number]),
                        indicator: 'green'
                    });
                } else if (r.message && r.message.length > 1) {
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

    frm.toggle_display('supplier_invoice_section', is_purchase);

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
    const d = new frappe.ui.Dialog({
        title: __('Multiple Jobs Found'),
        fields: [{ fieldtype: 'HTML', fieldname: 'job_list_html' }],
        size: 'large'
    });

    let html = '<table class="table table-bordered table-hover" style="margin:0">';
    html += '<thead><tr><th>Job ID</th><th>Customer</th><th>Customer Reference</th><th>BL Number</th><th></th></tr></thead><tbody>';
    jobs.forEach(job => {
        html += `<tr>
            <td>${frappe.utils.escape_html(job.name)}</td>
            <td>${frappe.utils.escape_html(job.customer || '')}</td>
            <td>${frappe.utils.escape_html(job.customer_reference || '')}</td>
            <td>${frappe.utils.escape_html(job.bl_number || '')}</td>
            <td><button class="btn btn-xs btn-primary select-job" data-job="${frappe.utils.escape_html(job.name)}">Select</button></td>
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
// Lock captured / linked entries
// ==========================================================

const LOCKED_STATUSES = new Set(['Captured', 'Issued to Client']);
const LOCKED_FIELDS = [
    'company', 'entry_type', 'entry_date', 'status', 'job_doctype',
    'bl_number_lookup', 'job_name', 'party_type', 'party',
    'supplier_invoice_no', 'supplier_invoice_date', 'currency',
    'conversion_rate', 'amount', 'tax_amount',
    'linked_purchase_invoice', 'linked_sales_invoice', 'charge_details'
];

function is_invoice_register_locked(frm) {
    return Boolean(
        LOCKED_STATUSES.has(frm.doc.status) ||
        frm.doc.linked_purchase_invoice ||
        frm.doc.linked_sales_invoice
    );
}

function apply_locked_entry_state(frm) {
    if (!is_invoice_register_locked(frm)) return;

    LOCKED_FIELDS.forEach(fieldname => {
        if (frm.fields_dict[fieldname]) {
            frm.set_df_property(fieldname, 'read_only', 1);
        }
    });

    if (frm.fields_dict.charge_details && frm.fields_dict.charge_details.grid) {
        frm.fields_dict.charge_details.grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
    }

    frm.dashboard.set_headline_alert(
        __('This Invoice Register Entry is locked because it has been captured or linked to an invoice.'),
        'orange'
    );
}


// ==========================================================
// Charge table totals
// ==========================================================

function calculate_charge_totals(frm) {
    const rows = frm.doc.charge_details || [];
    let total = 0;
    rows.forEach(row => {
        total += flt(row.line_amount);
    });
    frm.set_value('total_charge_amount', flt(total, 2));
    // Only drive amount from the table when rows exist;
    // otherwise preserve any manually entered value.
    if (rows.length) {
        frm.set_value('amount', flt(total, 2));
    }
}


// ==========================================================
// Status transition buttons
// ==========================================================

const STATUS_BUTTON_MAP = {
    // --- Purchase ---
    'Received': [
        { label: 'Submit for Approval', target: 'Submitted for Approval', color: 'primary' },
        { label: 'Cancel', target: 'Cancelled', color: 'danger' }
    ],
    // Issue 11 fix: three distinct approval paths, clearly named
    'Submitted for Approval': [
        { label: 'Approve — No Corrections Needed', target: 'Ready for Capture', color: 'success' },
        { label: 'Approve with Corrections Needed', target: 'Returned for Capture', color: 'primary' },
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

    // --- Sales ---
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

const COMMENT_REQUIRED = new Set(['Query with Supplier', 'Returned to Draft', 'Cancelled']);

function add_status_transition_buttons(frm) {
    const buttons = STATUS_BUTTON_MAP[frm.doc.status] || [];
    buttons.forEach(btn => {
        frm.add_custom_button(__(btn.label), function () {
            if (COMMENT_REQUIRED.has(btn.target)) {
                show_status_change_dialog(frm, btn.target, btn.label);
            } else {
                execute_status_change(frm, btn.target);
            }
        }, __('Actions'));
    });
}

function add_forwarding_working_cost_button(frm) {
    const can_copy =
        !frm.is_new() &&
        !is_invoice_register_locked(frm) &&
        frm.doc.entry_type === 'Purchase' &&
        frm.doc.job_doctype === 'Forwarding Job' &&
        frm.doc.job_name &&
        ['Ready for Capture', 'Returned for Capture'].includes(frm.doc.status) &&
        (frm.doc.charge_details || []).length;

    if (!can_copy) return;

    frm.add_custom_button(__('Copy to Forwarding Job Working Cost'), function () {
        if (frm.is_dirty()) {
            frappe.msgprint(__('Please save this Invoice Register Entry before copying charges.'));
            return;
        }
        frappe.call({
            method: 'copy_charges_to_forwarding_working_cost',
            doc: frm.doc,
            freeze: true,
            freeze_message: __('Copying charges to Forwarding Job...'),
            callback(r) {
                if (r && !r.exc && r.message && r.message.job_name) {
                    frm.reload_doc();
                    frappe.confirm(
                        __('Charges copied to Forwarding Job {0}. Open the Forwarding Job now?', [r.message.job_name]),
                        () => frappe.set_route('Form', 'Forwarding Job', r.message.job_name)
                    );
                }
            }
        });
    }, __('Actions'));
}

function show_status_change_dialog(frm, target_status, button_label) {
    const d = new frappe.ui.Dialog({
        title: __(button_label),
        fields: [{
            label: __('Comment'),
            fieldname: 'comment',
            fieldtype: 'Small Text',
            reqd: 1,
            description: __('Please provide a reason for this status change')
        }],
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
        args: { new_status: target_status, comment: comment || '' },
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
