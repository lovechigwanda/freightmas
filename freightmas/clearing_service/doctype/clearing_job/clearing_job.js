// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Clearing Job", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Clearing Job', {
  refresh: function(frm) {
    toggle_fields(frm);
  },

  // Triggers
  bl_type: function(frm) {
    toggle_fields(frm);
  },
  is_telex_confirmed: function(frm) {
    toggle_fields(frm);
  },
  is_discharged_from_vessel: function(frm) {
    toggle_fields(frm);
  },
  is_discharged_from_port: function(frm) {
    toggle_fields(frm);
  },
  is_sl_invoice_received: function(frm) {
    toggle_fields(frm);
  },
  is_do_received: function(frm) {
    toggle_fields(frm);
  },
  is_booking_confirmed: function(frm) {
    toggle_fields(frm);
  },
  is_sl_invoice_paid: function(frm) {
    toggle_fields(frm);
  },
  is_do_requested: function(frm) {
    toggle_fields(frm);
  },

  validate: function(frm) {
    let missing_fields = [];

    if (frm.doc.bl_type === 'OBL' && !frm.doc.obl_received_date) {
      missing_fields.push("OBL Received Date");
    }

    if (frm.doc.bl_type === 'Telex Release') {
      if (!frm.doc.is_telex_confirmed) {
        missing_fields.push("Is Telex Confirmed");
      }
      if (frm.doc.is_telex_confirmed && !frm.doc.telex_confirmed_date) {
        missing_fields.push("Telex Confirmed Date");
      }
    }

    if (frm.doc.is_discharged_from_vessel && !frm.doc.date_discharged_from_vessel) {
      missing_fields.push("Date Discharged from Vessel");
    }

    if (frm.doc.is_discharged_from_port && !frm.doc.date_discharged_from_port) {
      missing_fields.push("Date Discharged from Port");
    }

    if (frm.doc.is_sl_invoice_received && !frm.doc.sl_invoice_received_date) {
      missing_fields.push("SL Invoice Received Date");
    }

    if (frm.doc.is_do_received && !frm.doc.do_received_date) {
      missing_fields.push("DO Received Date");
    }

    if (frm.doc.is_booking_confirmed && !frm.doc.booking_confirmation_date) {
      missing_fields.push("Booking Confirmation Date");
    }

    if (frm.doc.is_sl_invoice_paid && !frm.doc.sl_invoice_payment_date) {
      missing_fields.push("SL Invoice Payment Date");
    }

    if (frm.doc.is_do_requested && !frm.doc.do_requested_date) {
      missing_fields.push("DO Requested Date");
    }

    if (missing_fields.length > 0) {
      frappe.msgprint({
        title: __('Missing Information'),
        indicator: 'orange',
        message: __('Please fill in the following fields before saving:') +
          '<ul><li>' + missing_fields.join('</li><li>') + '</li></ul>'
      });
      frappe.validated = false;
    }
  }
});

// Show/hide dependent fields
function toggle_fields(frm) {
  frm.set_df_property('obl_received_date', 'hidden', frm.doc.bl_type !== 'OBL');
  frm.set_df_property('is_telex_confirmed', 'hidden', frm.doc.bl_type !== 'Telex Release');
  frm.set_df_property('telex_confirmed_date', 'hidden', !frm.doc.is_telex_confirmed);

  frm.set_df_property('date_discharged_from_vessel', 'hidden', !frm.doc.is_discharged_from_vessel);
  frm.set_df_property('date_discharged_from_port', 'hidden', !frm.doc.is_discharged_from_port);
  frm.set_df_property('sl_invoice_received_date', 'hidden', !frm.doc.is_sl_invoice_received);
  frm.set_df_property('do_received_date', 'hidden', !frm.doc.is_do_received);
  frm.set_df_property('booking_confirmation_date', 'hidden', !frm.doc.is_booking_confirmed);
  frm.set_df_property('sl_invoice_payment_date', 'hidden', !frm.doc.is_sl_invoice_paid);
  frm.set_df_property('do_requested_date', 'hidden', !frm.doc.is_do_requested);
}

////////////////////////////////////////////////////////

//////////////HTML FOR MILESTONE TRACKER///////////////


frappe.ui.form.on('Clearing Job', {
  refresh(frm) {
    render_progress_dial_and_theme_chips(frm);
  },

  is_sl_invoice_received: render_progress_dial_and_theme_chips,
  is_discharged_from_vessel: render_progress_dial_and_theme_chips,
  is_discharged_from_port: render_progress_dial_and_theme_chips,
  is_do_requested: render_progress_dial_and_theme_chips,
  is_do_received: render_progress_dial_and_theme_chips,
  is_booking_confirmed: render_progress_dial_and_theme_chips,
  is_sl_invoice_paid: render_progress_dial_and_theme_chips
});

function render_progress_dial_and_theme_chips(frm) {
  if (!frm.fields_dict.milestone_tracker) return;

  const milestones = [
    { label: "SL Invoice Received", field: "is_sl_invoice_received" },
    { label: "Discharged from Vessel", field: "is_discharged_from_vessel" },
    { label: "Discharged from Port", field: "is_discharged_from_port" },
    { label: "DO Requested", field: "is_do_requested" },
    { label: "DO Received", field: "is_do_received" },
    { label: "Booking Confirmed", field: "is_booking_confirmed" },
    { label: "SL Invoice Paid", field: "is_sl_invoice_paid" }
  ];

  const completed = milestones.filter(m => frm.doc[m.field]).length;
  const total = milestones.length;
  const percent = Math.round((completed / total) * 100);

  let html = `
    <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 20px; margin-top: 10px;">
      <div style="flex: 0 0 100px; height: 100px; border-radius: 50%; border: 6px solid #e9ecef; position: relative;">
        <div style="
          position: absolute;
          top: 0; left: 0;
          width: 100%;
          height: 100%;
          border-radius: 50%;
          border: 6px solid #146c43;
          clip-path: polygon(50% 50%, 50% 0%, ${getCircularClipPath(percent)})
        "></div>
        <div style="
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          font-weight: bold;
          font-size: 14px;
        ">${percent}%</div>
      </div>

      <div style="flex: 1; display: flex; flex-wrap: wrap; gap: 8px;">
  `;

  milestones.forEach(m => {
    const done = frm.doc[m.field];
    const bg = done ? '#e6f4ea' : '#fbeaea';
    const color = done ? '#146c43' : '#b02a37';
    const icon = done ? '✔' : '⭕';

    html += `
      <div style="
        background: ${bg};
        color: ${color};
        padding: 4px 10px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: 1px solid ${color};
        transition: 0.2s ease;
      " title="${m.label}">
        ${icon} ${m.label}
      </div>
    `;
  });

  html += `
      </div>
    </div>
  `;

  frm.fields_dict.milestone_tracker.$wrapper.html(html);
}

function getCircularClipPath(percent) {
  const angle = (percent / 100) * 360;
  const r = 50;
  const x = r + r * Math.cos((angle - 90) * Math.PI / 180);
  const y = r + r * Math.sin((angle - 90) * Math.PI / 180);
  if (percent <= 50) {
    return `50% 50%, 50% 0%, ${x}% ${y}%`;
  } else {
    return `50% 50%, 50% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, ${x}% ${y}%`;
  }
}



/////////////////////////////////////////////////////////////////////////

///CALCULATIONS LOGIC

// --- CALCULATIONS LOGIC (With Multi-Currency & Base Fields Hidden) ---

frappe.ui.form.on('Clearing Job', {
    refresh(frm) {
        calculate_clearing_totals(frm);
        toggle_base_fields(frm);
    },
    validate(frm) {
        calculate_clearing_totals(frm);
    },
    currency(frm) {
        if (frm.doc.currency && frm.doc.base_currency && frm.doc.currency !== frm.doc.base_currency) {
            frappe.call({
                method: "erpnext.setup.utils.get_exchange_rate",
                args: {
                    from_currency: frm.doc.currency,
                    to_currency: frm.doc.base_currency
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("conversion_rate", r.message);
                        calculate_clearing_totals(frm);
                        toggle_base_fields(frm);
                    }
                }
            });
        } else {
            frm.set_value("conversion_rate", 1.0);
            calculate_clearing_totals(frm);
            toggle_base_fields(frm);
        }
    },
    conversion_rate(frm) {
        calculate_clearing_totals(frm);
    }
});

frappe.ui.form.on('Clearing Charges', {
    qty(frm, cdt, cdn) {
        update_charge_row(frm, cdt, cdn);
    },
    sell_rate(frm, cdt, cdn) {
        update_charge_row(frm, cdt, cdn);
    },
    buy_rate(frm, cdt, cdn) {
        update_charge_row(frm, cdt, cdn);
    },
    clearing_charges_remove(frm) {
        calculate_clearing_totals(frm);
    }
});

function update_charge_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    row.revenue_amount = (row.qty || 0) * (row.sell_rate || 0);
    row.cost_amount = (row.qty || 0) * (row.buy_rate || 0);
    frm.refresh_field('clearing_charges');
    calculate_clearing_totals(frm);
}

function calculate_clearing_totals(frm) {
    let total_revenue = 0;
    let total_cost = 0;

    (frm.doc.clearing_charges || []).forEach(row => {
        total_revenue += row.revenue_amount || 0;
        total_cost += row.cost_amount || 0;
    });

    const profit = total_revenue - total_cost;
    const rate = frm.doc.conversion_rate || 1.0;

    frm.set_value('total_estimated_revenue', total_revenue);
    frm.set_value('total_estimated_cost', total_cost);
    frm.set_value('total_estimated_profit', profit);

    frm.set_value('total_estimated_revenue_base', total_revenue * rate);
    frm.set_value('total_estimated_cost_base', total_cost * rate);
    frm.set_value('total_estimated_profit_base', profit * rate);
}

function toggle_base_fields(frm) {
    const is_same_currency = frm.doc.currency === frm.doc.base_currency;

    frm.toggle_display("total_estimated_revenue_base", !is_same_currency);
    frm.toggle_display("total_estimated_cost_base", !is_same_currency);
    frm.toggle_display("total_estimated_profit_base", !is_same_currency);
}

///////////////////////////////////////////////////////////////////////////////////


////DYNAMIC CURRENCY LABELS

frappe.ui.form.on("Clearing Job", {
    refresh(frm) {
        update_currency_labels(frm);
    },
    currency: function(frm) {
        update_currency_labels(frm);
    },
    base_currency: function(frm) {
        update_currency_labels(frm);
    }
});

function update_currency_labels(frm) {
    const currency = frm.doc.currency || "USD";
    const base_currency = frm.doc.base_currency || "USD";

    const label_map = {
        "total_estimated_revenue": __("Total Estimated Revenue ({0})", [currency]),
        "total_estimated_cost": __("Total Estimated Cost ({0})", [currency]),
        "total_estimated_profit": __("Total Estimated Profit ({0})", [currency]),
        "total_estimated_revenue_base": __("Total Estimated Revenue ({0})", [base_currency]),
        "total_estimated_cost_base": __("Total Estimated Cost ({0})", [base_currency]),
        "total_estimated_profit_base": __("Total Estimated Profit ({0})", [base_currency])
    };

    for (const [fieldname, label] of Object.entries(label_map)) {
        if (frm.fields_dict[fieldname]) {
            frm.fields_dict[fieldname].df.label = label;
            frm.refresh_field(fieldname);
        }
    }
}


////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////
// CREATE SALES INVOICE FROM CLEARING CHARGES
///////////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Clearing Job', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button('Sales Invoice', () => {
        const all_rows = frm.doc.clearing_charges || [];
        const eligible_rows = all_rows.filter(row => !row.is_invoiced && !row.sales_invoice_reference);

        if (!eligible_rows.length) {
          frappe.msgprint("No eligible charges found for invoicing.");
          return;
        }

        let selected_customer = eligible_rows[0].customer;

        const get_unique_customers = () => [...new Set(eligible_rows.map(r => r.customer))];

        const render_dialog_ui = (dialog, customer) => {
          const customers = get_unique_customers();
          const rows = customer ? eligible_rows.filter(r => r.customer === customer) : eligible_rows;

          const customer_filter = `
            <div style="margin-bottom: 10px;">
              <label for="customer-filter">Customer:</label>
              <select id="customer-filter" class="form-control">
                <option value="">-- All --</option>
                ${customers.map(c =>
                  `<option value="${c}" ${c === customer ? 'selected' : ''}>${c}</option>`
                ).join('')}
              </select>
            </div>
          `;

          const table = `
            <table class="table table-bordered table-sm">
              <thead>
                <tr>
                  <th></th>
                  <th>Customer</th>
                  <th>Charge</th>
                  <th>Rate</th>
                  <th>Qty</th>
                </tr>
              </thead>
              <tbody>
                ${rows.map(row => `
                  <tr>
                    <td><input type="checkbox" class="charge-row-check" data-row-name="${row.name}"></td>
                    <td>${row.customer}</td>
                    <td>${row.charge}</td>
                    <td>${frappe.format(row.revenue_amount, { fieldtype: 'Currency' })}</td>
                    <td>${row.qty}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;

          dialog.fields_dict.charge_rows_html.$wrapper.html(customer_filter + table);

          dialog.$wrapper.find('#customer-filter').on('change', function () {
            selected_customer = this.value;
            render_dialog_ui(dialog, selected_customer);
          });
        };

        const dialog = new frappe.ui.Dialog({
          title: 'Select Charges to Invoice',
          fields: [
            {
              fieldtype: 'HTML',
              fieldname: 'charge_rows_html',
              options: ''
            }
          ],
          primary_action_label: 'Create Sales Invoice',
          primary_action() {
            const selected = Array.from(
              dialog.$wrapper.find('.charge-row-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
              frappe.msgprint("Please select at least one row.");
              return;
            }

            const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
            const unique_customers = [...new Set(selected_rows.map(r => r.customer))];

            if (unique_customers.length > 1) {
              frappe.msgprint("You can only create an invoice for one customer at a time.");
              return;
            }

            frappe.call({
              method: "freightmas.clearing_service.doctype.clearing_job.clearing_job.create_sales_invoice_with_rows",
              args: {
                docname: frm.doc.name,
                row_names: selected
              },
              callback(r) {
                if (r.message) {
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
      }, __("Create"));
    }
  }
});

///////////////////////////////////////////////////////////////////////////////
// CREATE PURCHASE INVOICE FROM CLEARING CHARGES
///////////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Clearing Job', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button('Purchase Invoice', () => {
        const all_rows = frm.doc.clearing_charges || [];
        const eligible_rows = all_rows.filter(row => !row.is_purchased && !row.purchase_invoice_reference);

        if (!eligible_rows.length) {
          frappe.msgprint("No eligible charges found for purchase invoicing.");
          return;
        }

        let selected_supplier = eligible_rows[0].supplier;

        const get_unique_suppliers = () => [...new Set(eligible_rows.map(r => r.supplier))];

        const render_dialog_ui = (dialog, supplier) => {
          const suppliers = get_unique_suppliers();
          const rows = supplier ? eligible_rows.filter(r => r.supplier === supplier) : eligible_rows;

          const supplier_filter = `
            <div style="margin-bottom: 10px;">
              <label for="supplier-filter">Supplier:</label>
              <select id="supplier-filter" class="form-control">
                <option value="">-- All --</option>
                ${suppliers.map(s =>
                  `<option value="${s}" ${s === supplier ? 'selected' : ''}>${s}</option>`
                ).join('')}
              </select>
            </div>
          `;

          const table = `
            <table class="table table-bordered table-sm">
              <thead>
                <tr>
                  <th></th>
                  <th>Supplier</th>
                  <th>Charge</th>
                  <th>Rate</th>
                  <th>Qty</th>
                </tr>
              </thead>
              <tbody>
                ${rows.map(row => `
                  <tr>
                    <td><input type="checkbox" class="charge-row-check" data-row-name="${row.name}"></td>
                    <td>${row.supplier}</td>
                    <td>${row.charge}</td>
                    <td>${frappe.format(row.buy_rate, { fieldtype: 'Currency' })}</td>
                    <td>${row.qty}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;

          dialog.fields_dict.charge_rows_html.$wrapper.html(supplier_filter + table);

          dialog.$wrapper.find('#supplier-filter').on('change', function () {
            selected_supplier = this.value;
            render_dialog_ui(dialog, selected_supplier);
          });
        };

        const dialog = new frappe.ui.Dialog({
          title: 'Select Charges for Purchase Invoice',
          fields: [
            {
              fieldtype: 'HTML',
              fieldname: 'charge_rows_html',
              options: ''
            }
          ],
          primary_action_label: 'Create Purchase Invoice',
          primary_action() {
            const selected = Array.from(
              dialog.$wrapper.find('.charge-row-check:checked')
            ).map(el => el.dataset.rowName);

            if (!selected.length) {
              frappe.msgprint("Please select at least one row.");
              return;
            }

            const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
            const unique_suppliers = [...new Set(selected_rows.map(r => r.supplier))];

            if (unique_suppliers.length > 1) {
              frappe.msgprint("You can only create an invoice for one supplier at a time.");
              return;
            }

            frappe.call({
              method: "freightmas.clearing_service.doctype.clearing_job.clearing_job.create_purchase_invoice_with_rows",
              args: {
                docname: frm.doc.name,
                row_names: selected
              },
              callback(r) {
                if (r.message) {
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
      }, __("Create"));
    }
  }
});

///////////////////////////////////////////////////////////////////////////////
// FIELD LOCKING + DELETION PREVENTION FOR INVOICED CHARGES
///////////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Clearing Charges', {
  form_render(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const grid_row = frm.fields_dict.clearing_charges.grid.grid_rows_by_docname[cdn];

    if (row.sales_invoice_reference) {
      grid_row.toggle_editable('sell_rate', false);
      grid_row.toggle_editable('customer', false);
      grid_row.toggle_editable('qty', false);
    }

    if (row.purchase_invoice_reference) {
      grid_row.toggle_editable('buy_rate', false);
      grid_row.toggle_editable('supplier', false);
      grid_row.toggle_editable('qty', false);
    }
  },

  before_clearing_charges_remove(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    if (row.sales_invoice_reference || row.purchase_invoice_reference) {
      frappe.throw(__("You cannot delete a charge that is already invoiced."));
    }
  }
});

/////////////////////////////////////////////////////////////////////////////////

// ////////////////////////////////////////////////////////////////////////////
// UPDATE CURRENT MILESTONE SECTION FROM LAST ROW OF CLEARING TRACKING TABLE
// ////////////////////////////////////////////////////////////////////////////

frappe.ui.form.on('Clearing Job', {
  before_save: function(frm) {
    const tracking = frm.doc.clearing_tracking;
    if (tracking && tracking.length > 0) {
      const last = tracking[tracking.length - 1];

      frm.set_value('current_milestone', last.milestone);
      frm.set_value('current_comment', last.comment);
      frm.set_value('last_updated_on', last.updated_on);
      frm.set_value('last_updated_by', last.updated_by);
    }
  }
});

/////////////////////////////////////////////////////////////////////////////////////
