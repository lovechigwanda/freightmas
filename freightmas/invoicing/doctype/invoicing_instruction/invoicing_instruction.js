// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoicing Instruction', {
    refresh(frm) {
        // ========================================
        // FETCH CHARGES BUTTON (before submit only)
        // ========================================
        if (frm.doc.docstatus === 0 && frm.doc.forwarding_job) {
            frm.add_custom_button(__('Fetch Charges from Job'), function () {
                frappe.call({
                    method: 'fetch_charges_from_job',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Fetching uninvoiced charges...'),
                    callback(r) {
                        if (r && r.message !== undefined) {
                            if (r.message > 0) {
                                frm.reload_doc();
                            }
                        }
                    }
                });
            });
        }

        // ========================================
        // STATUS INDICATOR
        // ========================================
        const colours = {
            'Draft': 'red',
            'Submitted': 'blue',
            'Actioned': 'green',
            'Cancelled': 'grey'
        };
        if (frm.doc.status && colours[frm.doc.status]) {
            frm.page.set_indicator(__(frm.doc.status), colours[frm.doc.status]);
        }
    },

    forwarding_job(frm) {
        // Reset line items when job changes (draft only)
        if (frm.doc.docstatus === 0) {
            frm.clear_table('line_items');
            frm.refresh_field('line_items');
        }
    }
});

// ========================================
// Calculate line item amounts
// ========================================
frappe.ui.form.on('Invoicing Instruction Item', {
    qty(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    sell_rate(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    line_items_remove(frm) {
        calculate_instruction_totals(frm);
    }
});

function calculate_item_amount(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    const qty = flt(row.qty) || 1;
    const rate = flt(row.sell_rate);
    frappe.model.set_value(cdt, cdn, 'amount', flt(qty * rate, 2));
    calculate_instruction_totals(frm);
}

function calculate_instruction_totals(frm) {
    let total = 0;
    let count = 0;
    (frm.doc.line_items || []).forEach(item => {
        total += flt(item.amount);
        count += 1;
    });
    frm.set_value('total_amount', flt(total, 2));
    frm.set_value('total_items', count);
}
