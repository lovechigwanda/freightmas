frappe.ui.form.on('Quotation', {
    items_on_form_rendered(frm) {
        calculate_totals(frm);
    },
    items_add(frm) {
        calculate_totals(frm);
    },
    items_remove(frm) {
        calculate_totals(frm);
    },
    refresh(frm) {
        calculate_totals(frm);

        // Only show the button if the document is saved (not new)
        if (!frm.is_new()) {
            frm.add_custom_button('View Cost Sheet', function() {
                window.open(
                    `/printview?doctype=Quotation&name=${frm.doc.name}&format=Quotation%20Cost%20Sheet&no_letterhead=1`,
                    '_blank'
                );
            });
        }
    },
    validate(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let est_revenue = 0;
    let est_cost = 0;

    (frm.doc.items || []).forEach(item => {
        est_revenue += flt(item.amount);
        est_cost += flt(item.cost_amount);
    });

    frm.set_value('est_revenue', est_revenue);
    frm.set_value('est_cost', est_cost);
    frm.set_value('est_profit', est_revenue - est_cost);
}

frappe.ui.form.on('Quotation Item', {
    qty(frm, cdt, cdn) {
        update_cost_amount(frm, cdt, cdn);
    },
    buy_rate(frm, cdt, cdn) {
        update_cost_amount(frm, cdt, cdn);
    }
});

function update_cost_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "cost_amount", (row.qty || 0) * (row.buy_rate || 0));
    calculate_totals(frm);
}
