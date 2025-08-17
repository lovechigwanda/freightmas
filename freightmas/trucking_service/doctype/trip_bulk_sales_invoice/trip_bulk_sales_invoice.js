// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Trip Bulk Sales Invoice', {
    refresh(frm) {
        calculate_totals(frm);
    },
    trip_bulk_sales_invoice_item_on_form_rendered(frm) {
        calculate_totals(frm);
    },
    trip_bulk_sales_invoice_item_add(frm) {
        calculate_totals(frm);
    },
    trip_bulk_sales_invoice_item_remove(frm) {
        calculate_totals(frm);
    },
    trip_bulk_sales_invoice_item: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let sub_total = 0;
    let vat = 0;
    let grand_total = 0;
    let total_quantity = 0;

    (frm.doc.trip_bulk_sales_invoice_item || []).forEach(row => {
        sub_total += flt(row.amount || 0);
        total_quantity += flt(row.qty || 0);
    });

    vat = 0; // Always zero as per your instruction
    grand_total = sub_total + vat;

    frm.set_value('sub_total', sub_total);
    frm.set_value('vat', vat);
    frm.set_value('grand_total', grand_total);
    frm.set_value('total_quantity', total_quantity);
}
