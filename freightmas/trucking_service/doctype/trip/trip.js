// Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

///////////////////////////////////////////////////////////////////////////////////////////////

// CALCULATE PROFIT IN TRIP DOCTYPE
frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        calculate_totals(frm);
    },
    validate: function(frm) {
        calculate_totals(frm);
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
            frm.set_value('current_trip_milestone', lastRow.trip_milestone);
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
//CREATE SALES INVOICE FROM TRIP REVENUE CHARGES
frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        frm.add_custom_button('Sales Invoice', () => {
            let dialog = new frappe.ui.Dialog({
                title: 'Create Sales Invoice',
                fields: [
                    {
                        fieldtype: 'Link',
                        fieldname: 'receivable_party',
                        options: 'Customer',
                        label: 'Receivable Party',
                        reqd: 1,
                        onchange: function () {
                            const receivable_party = dialog.get_value('receivable_party');
                            const charges = frm.doc.trip_revenue_charges.filter(c => {
                                return !c.is_invoiced && c.receivable_party === receivable_party;
                            });
                            dialog.fields_dict.charges.df.data = charges;
                            dialog.fields_dict.charges.refresh();
                        },
                    },
                    {
                        fieldtype: 'Table',
                        fieldname: 'charges',
                        label: 'Select Charges',
                        fields: [
                            { fieldtype: 'Data', fieldname: 'name', label: 'ID', hidden: 1 },
                            { fieldtype: 'Data', fieldname: 'charge', label: 'Charge', in_list_view: 1 },
                            { fieldtype: 'Data', fieldname: 'charge_description', label: 'Description', in_list_view: 1 },
                            { fieldtype: 'Int', fieldname: 'quantity', label: 'Quantity', in_list_view: 1 },
                            { fieldtype: 'Float', fieldname: 'rate', label: 'Rate', in_list_view: 1 },
                        ],
                        data: [],
                        get_data: function () {
                            const receivable_party = dialog.get_value('receivable_party');
                            return frm.doc.trip_revenue_charges.filter(c => {
                                return !c.is_invoiced && c.receivable_party === receivable_party;
                            });
                        },
                    },
                ],
                primary_action_label: 'Create Invoice',
                primary_action: function () {
                    const values = dialog.get_values();
                    if (!values || !values.receivable_party || !values.charges || values.charges.length === 0) {
                        frappe.msgprint('Please select a receivable party and at least one charge to invoice.');
                        return;
                    }
                    const selected_charges = values.charges.map(c => c.name);
                    frappe.call({
                        method: 'freightmas.trucking_service.doctype.trip.trip.create_sales_invoice',
                        args: {
                            trip_name: frm.doc.name,
                            selected_charges,
                            receivable_party: values.receivable_party,
                        },
                        callback: function (response) {
                            if (response.message) {
                                frappe.msgprint(`Invoice Created: ${response.message.invoice_name}`);
                                frappe.set_route('Form', 'Sales Invoice', response.message.invoice_name);
                                frm.reload_doc();
                            }
                        },
                    });
                    dialog.hide();
                },
            });
            dialog.show();
        }, 'Create');
    }
});

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

/////////////////////////////////////////////////////////////////////////
////CREATE PURCHASE INVOICE FROM TRIP COST CHARGES
frappe.ui.form.on('Trip', {
    refresh: function (frm) {
        frm.add_custom_button('Purchase Invoice', () => {
            let dialog = new frappe.ui.Dialog({
                title: 'Create Purchase Invoice',
                fields: [
                    {
                        fieldtype: 'Link',
                        fieldname: 'supplier',
                        options: 'Supplier',
                        label: 'Supplier',
                        reqd: 1,
                        onchange: function () {
                            const supplier = dialog.get_value('supplier');
                            const charges = frm.doc.trip_cost_charges.filter(c => {
                                return !c.is_invoiced && c.payable_party === supplier;
                            });
                            dialog.fields_dict.charges.df.data = charges;
                            dialog.fields_dict.charges.refresh();
                        },
                    },
                    {
                        fieldtype: 'Table',
                        fieldname: 'charges',
                        label: 'Select Charges',
                        fields: [
                            { fieldtype: 'Data', fieldname: 'name', label: 'ID', hidden: 1 },
                            { fieldtype: 'Data', fieldname: 'charge', label: 'Charge', in_list_view: 1 },
                            { fieldtype: 'Data', fieldname: 'charge_description', label: 'Description', in_list_view: 1 },
                            { fieldtype: 'Int', fieldname: 'quantity', label: 'Quantity', in_list_view: 1 },
                            { fieldtype: 'Float', fieldname: 'rate', label: 'Rate', in_list_view: 1 },
                        ],
                        data: [],
                        get_data: function () {
                            const supplier = dialog.get_value('supplier');
                            return frm.doc.trip_cost_charges.filter(c => {
                                return !c.is_invoiced && c.payable_party === supplier;
                            });
                        },
                    },
                ],
                primary_action_label: 'Create Purchase Invoice',
                primary_action: function () {
                    const values = dialog.get_values();
                    if (!values || !values.supplier || !values.charges || values.charges.length === 0) {
                        frappe.msgprint('Please select a supplier and at least one charge to include in the invoice.');
                        return;
                    }
                    const selected_charges = values.charges.map(c => c.name);
                    frappe.call({
                        method: 'freightmas.trucking_service.doctype.trip.trip.create_purchase_invoice',
                        args: {
                            trip_name: frm.doc.name,
                            selected_charges,
                            supplier: values.supplier,
                        },
                        callback: function (response) {
                            if (response.message) {
                                frappe.msgprint(`Purchase Invoice Created: <a href="/app/purchase-invoice/${response.message.invoice_name}">${response.message.invoice_name}</a>`);
                                frappe.set_route('Form', 'Purchase Invoice', response.message.invoice_name);
                                frm.reload_doc();
                            }
                        },
                    });
                    dialog.hide();
                },
            });
            dialog.show();
        }, 'Create');
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

/////////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Trip', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button('Fuel Issue', () => {
        let rows = frm.doc.trip_fuel_allocation || [];

        // Filter out already issued rows
        const eligible_rows = rows.filter(row => !row.is_invoiced && !row.stock_entry_reference);
        if (!eligible_rows.length) {
          frappe.msgprint("No eligible fuel allocation rows found.");
          return;
        }

        // Build HTML table-like rows
        let html = `
          <table class="table table-bordered table-sm">
            <thead>
              <tr>
                <th style="width: 5%"></th>
                <th>Item</th>
                <th>Qty (L)</th>
                <th>Rate</th>
                <th>Amount</th>
                <th>Warehouse</th>
              </tr>
            </thead>
            <tbody>`;

        eligible_rows.forEach(row => {
          html += `
            <tr>
              <td><input type="checkbox" class="fuel-row-check" data-row-name="${row.name}"></td>
              <td>${row.item}</td>
              <td>${row.qty}</td>
              <td>${row.rate || 0}</td>
              <td>${(row.qty * (row.rate || 0)).toFixed(2)}</td>
              <td>${row.s_warehouse}</td>
            </tr>`;
        });

        html += `</tbody></table>`;

        const d = new frappe.ui.Dialog({
          title: 'Select Fuel Allocation Rows',
          fields: [
            {
              fieldtype: 'HTML',
              fieldname: 'fuel_rows_html',
              options: html
            }
          ],
          primary_action_label: 'Create Stock Entry',
          primary_action() {
            const selected = Array.from(
              d.$wrapper.find('.fuel-row-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
              frappe.msgprint("Please select at least one row.");
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
                  frappe.set_route("Form", "Stock Entry", r.message);
                  frm.reload_doc();
                  d.hide();
                }
              }
            });
          }
        });

        d.show();
      }, __("Create"));
    }
  }
});

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

//////////////////////////////////////////////////////////////

//// CREATE JOURNAL ENTRIES FROM TRIP OTHER COSTS

frappe.ui.form.on('Trip', {
  refresh(frm) {
    if (!frm.is_new()) {

      // ==============================
      // OTHER CHARGES → JOURNAL ENTRY
      // ==============================

      frm.add_custom_button('Other Charges Journal Entry', () => {
        let rows = frm.doc.trip_other_costs || [];

        // Filter eligible rows (not journaled or invoiced)
        const eligible_rows = rows.filter(row => !row.is_invoiced && !row.journal_entry);
        if (!eligible_rows.length) {
          frappe.msgprint("No eligible 'Other Costs' rows found.");
          return;
        }

        // Build HTML preview
            let html = `
  <table class="table table-bordered table-sm">
    <thead>
      <tr>
        <th style="width: 5%"></th>
        <th>Charge</th>
        <th>Description</th>
        <th>Qty</th>
        <th>Rate</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
`;

eligible_rows.forEach(row => {
  html += `
    <tr>
      <td><input type="checkbox" class="other-costs-check" data-row-name="${row.name}"></td>
      <td>${row.item_code}</td>
      <td>${row.description || ''}</td>
      <td>${row.quantity}</td>
      <td>${row.rate}</td>
      <td>${(row.quantity * row.rate).toFixed(2)}</td>
    </tr>
  `;
});

html += `</tbody></table>`;


        // Create dialog
        const d = new frappe.ui.Dialog({
          title: 'Select Other Charges',
          fields: [
            {
              fieldtype: 'HTML',
              fieldname: 'other_costs_html',
              options: html
            }
          ],
          primary_action_label: 'Create Journal Entry',
          primary_action() {
            const selected = Array.from(
              d.$wrapper.find('.other-costs-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
              frappe.msgprint("Please select at least one row.");
              return;
            }

            frappe.call({
              method: "freightmas.trucking_service.doctype.trip.trip.create_journal_entry_from_other_costs",
              args: {
                docname: frm.doc.name,
                row_names: selected
              },
              callback(r) {
                if (r.message) {
                  frappe.set_route("Form", "Journal Entry", r.message);
                  frm.reload_doc();
                  d.hide();
                }
              }
            });
          }
        });

        d.show();
      }, __("Create"));
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


//////////////////////////////////////////////////////////////

frappe.ui.form.on('Trip', {
  refresh(frm) {
    if (!frm.is_new()) {

      // ================================
      // TRIP COMMISSIONS → PAYROLL ENTRY
      // ================================

      frm.add_custom_button('Post Trip Commissions to Payroll', () => {
        let rows = frm.doc.trip_commissions || [];

        // Filter eligible rows (not posted to payroll yet)
        const eligible_rows = rows.filter(row => !row.is_posted_to_payroll && !row.payroll_entry);
        if (!eligible_rows.length) {
          frappe.msgprint("No eligible 'Trip Commissions' rows found.");
          return;
        }

        // Build HTML preview
        let html = `
          <table class="table table-bordered table-sm">
            <thead>
              <tr>
                <th style="width: 5%"></th>
                <th>Driver</th>
                <th>Employee</th>
                <th>Component</th>
                <th>Description</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
        `;

        eligible_rows.forEach(row => {
          html += `
            <tr>
              <td><input type="checkbox" class="commission-check" data-row-name="${row.name}"></td>
              <td>${row.driver}</td>
              <td>${row.employee || ''}</td>
              <td>${row.salary_component}</td>
              <td>${row.description || ''}</td>
              <td>${frappe.format(row.amount, { fieldtype: 'Currency' })}</td>
            </tr>
          `;
        });

        html += `</tbody></table>`;

        // Create dialog
        const d = new frappe.ui.Dialog({
          title: 'Select Trip Commissions',
          fields: [
            {
              fieldtype: 'HTML',
              fieldname: 'trip_commissions_html',
              options: html
            }
          ],
          primary_action_label: 'Post to Payroll',
          primary_action() {
            const selected = Array.from(
              d.$wrapper.find('.commission-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
              frappe.msgprint("Please select at least one row.");
              return;
            }

            frappe.call({
              method: "freightmas.trucking_service.doctype.trip.trip.create_additional_salary_from_trip_commissions",
              args: {
                docname: frm.doc.name,
                row_names: selected
              },
              callback(r) {
                if (r.message) {
                  frappe.msgprint("Trip Commissions successfully posted to payroll.");
                  frm.reload_doc();
                  d.hide();
                }
              }
            });
          }
        });

        d.show();
      }, __("Create"));
    }
  }
});


/////////////////////////////////////////////////


frappe.ui.form.on('Trip Commissions', {
  before_trip_commissions_remove(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    if (row.is_posted_to_payroll || row.payroll_entry) {
      frappe.throw(__("You cannot delete a commission row that has been posted to payroll."));
    }
  }
});
////////////////////////////////////////////