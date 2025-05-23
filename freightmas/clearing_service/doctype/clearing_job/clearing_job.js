// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Clearing Job", {
// 	refresh(frm) {

// 	},
// });

// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// For license information, please see license.txt

frappe.ui.form.on('Clearing Job', {

  // When the form is refreshed
  refresh: function(frm) {
    toggle_fields(frm);  // Control visibility of fields based on values
  },

  // Triggered when BL Type is changed
  bl_type: function(frm) {
    toggle_fields(frm);  // Reevaluate field visibility
  },

  // Triggered when Telex checkbox is changed
  is_telex_confirmed: function(frm) {
    toggle_fields(frm);
  },

  // Other field triggers (used to toggle date fields)
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

  // Validation before saving the form
  validate: function(frm) {
    let missing_fields = [];
    const bl_type = (frm.doc.bl_type || '').trim();

    // Check OBL requirement
    if (bl_type === 'OBL' && !frm.doc.obl_received_date) {
      missing_fields.push("OBL Received Date");
    }

    // Check Telex fields
    if (bl_type === 'Telex Release') {
      if (!frm.doc.is_telex_confirmed) {
        missing_fields.push("Is Telex Confirmed");
      }
      if (frm.doc.is_telex_confirmed && !frm.doc.telex_confirmed_date) {
        missing_fields.push("Telex Confirmed Date");
      }
    }

    // Check discharge and invoice-related flags and dates
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

    // Show error message if any required field is missing
    if (missing_fields.length > 0) {
      frappe.msgprint({
        title: __('Missing Information'),
        indicator: 'orange',
        message: __('Please fill in the following fields before saving:') +
          '<ul><li>' + missing_fields.join('</li><li>') + '</li></ul>'
      });
      frappe.validated = false;  // Prevent form submission
    }
  }
});


// Function to show/hide and enforce required fields dynamically
function toggle_fields(frm) {
  const bl_type = (frm.doc.bl_type || '').trim();

  // Show OBL Received Date only if BL Type is OBL
  frm.set_df_property('obl_received_date', 'hidden', bl_type !== 'OBL');

  // Show Telex fields only if BL Type is Telex Release
  frm.set_df_property('is_telex_confirmed', 'hidden', bl_type !== 'Telex Release');

  // Show Telex Confirmed Date only if checkbox is ticked
  frm.set_df_property('telex_confirmed_date', 'hidden', !(bl_type === 'Telex Release' && frm.doc.is_telex_confirmed));

  // Make Telex Confirmed Date mandatory only when visible
  frappe.meta.get_docfield('Clearing Job', 'telex_confirmed_date', frm.doc.name).reqd = (bl_type === 'Telex Release' && frm.doc.is_telex_confirmed);

  // Show/hide date fields for other boolean flags
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

// =============================================
// D&D AND PORT STORAGE DAYS - AUTO CALCULATION
// With support for to_be_returned toggle
// =============================================

// --- Parent field triggers ---
frappe.ui.form.on('Clearing Job', {
    discharge_date: function(frm) {
        update_all_dnd_storage(frm);
    },

    dnd_free_days: function(frm) {
        update_all_dnd_storage(frm);
    },

    port_free_days: function(frm) {
        update_all_dnd_storage(frm);
    },

    onload: function(frm) {
        update_all_dnd_storage(frm);
    },

    refresh: function(frm) {
        update_all_dnd_storage(frm);
    }
});

// --- Container table triggers ---
frappe.ui.form.on('Container Details', {
    gate_out_full_date: function(frm, cdt, cdn) {
        calculate_container_dnd_and_storage(frm, cdt, cdn);
        update_total_dnd_days(frm);
        update_total_storage_days(frm);
    },
    gate_in_empty_date: function(frm, cdt, cdn) {
        calculate_container_dnd_and_storage(frm, cdt, cdn);
        update_total_dnd_days(frm);
        update_total_storage_days(frm);
    },
    to_be_returned: function(frm, cdt, cdn) {
        calculate_container_dnd_and_storage(frm, cdt, cdn);
        update_total_dnd_days(frm);
        update_total_storage_days(frm);
    }
});

// --- General cargo table triggers ---
frappe.ui.form.on('General Cargo Details', {
    gate_out_date: function(frm, cdt, cdn) {
        calculate_general_dnd_storage(frm, cdt, cdn);
        update_total_dnd_days(frm);
        update_total_storage_days(frm);
    },
    gate_in_date: function(frm, cdt, cdn) {
        calculate_general_dnd_storage(frm, cdt, cdn);
        update_total_dnd_days(frm);
        update_total_storage_days(frm);
    },
    to_be_returned: function(frm, cdt, cdn) {
        calculate_general_dnd_storage(frm, cdt, cdn);
        update_total_dnd_days(frm);
        update_total_storage_days(frm);
    }
});

// --- Parent-level D&D + storage reference dates ---
function update_all_dnd_storage(frm) {
    const { discharge_date, dnd_free_days, port_free_days } = frm.doc;
    const today = frappe.datetime.get_today();

    if (discharge_date && dnd_free_days !== null && !isNaN(dnd_free_days)) {
        const last_free_dnd_day = dnd_free_days > 0
            ? frappe.datetime.add_days(discharge_date, dnd_free_days - 1)
            : frappe.datetime.add_days(discharge_date, -1);
        frm.set_value('last_free_dnd_day', last_free_dnd_day);
        frm.set_value('dnd_start_date', frappe.datetime.add_days(last_free_dnd_day, 1));
    }

    if (discharge_date && port_free_days !== null && !isNaN(port_free_days)) {
        const port_last_free_day = port_free_days > 0
            ? frappe.datetime.add_days(discharge_date, port_free_days - 1)
            : frappe.datetime.add_days(discharge_date, -1);
        frm.set_value('port_last_free_day', port_last_free_day);
        frm.set_value('port_storage_start_date', frappe.datetime.add_days(port_last_free_day, 1));
    }

    (frm.doc.container_details || []).forEach(row => {
        calculate_container_dnd_and_storage(frm, null, row.name);
    });
    (frm.doc.general_cargo_details || []).forEach(row => {
        calculate_general_dnd_storage(frm, null, row.name);
    });

    frm.refresh_field('container_details');
    frm.refresh_field('general_cargo_details');
    update_total_dnd_days(frm);
    update_total_storage_days(frm);
}

// --- Container-level logic with to_be_returned check ---
function calculate_container_dnd_and_storage(frm, cdt, cdn) {
    const row = locals[cdt || "Container Details"][cdn];
    const { discharge_date, dnd_free_days, port_free_days } = frm.doc;
    const today = frappe.datetime.get_today();

    // D&D
    if (!discharge_date || dnd_free_days === null || isNaN(dnd_free_days)) {
        row.dnd_days_accumulated = 0;
    } else {
        const last_free_dnd_day = dnd_free_days > 0
            ? frappe.datetime.add_days(discharge_date, dnd_free_days - 1)
            : frappe.datetime.add_days(discharge_date, -1);
        const dnd_start_date = frappe.datetime.add_days(last_free_dnd_day, 1);

        const dnd_end = row.to_be_returned
            ? row.gate_in_empty_date || today
            : row.gate_out_full_date || today;

        if (row.gate_out_full_date === discharge_date) {
            row.dnd_days_accumulated = 0;
        } else if (frappe.datetime.obj_to_str(dnd_end) > frappe.datetime.obj_to_str(last_free_dnd_day)) {
            row.dnd_days_accumulated = frappe.datetime.get_diff(dnd_end, dnd_start_date) + 1;
        } else {
            row.dnd_days_accumulated = 0;
        }
    }

    // Port Storage
    if (!discharge_date || port_free_days === null || isNaN(port_free_days)) {
        row.storage_days_accumulated = 0;
    } else {
        const port_last_free_day = port_free_days > 0
            ? frappe.datetime.add_days(discharge_date, port_free_days - 1)
            : frappe.datetime.add_days(discharge_date, -1);
        const port_storage_start_date = frappe.datetime.add_days(port_last_free_day, 1);
        const storage_end_date = row.gate_out_full_date || today;

        if (frappe.datetime.obj_to_str(storage_end_date) >= frappe.datetime.obj_to_str(port_storage_start_date)) {
            row.storage_days_accumulated = frappe.datetime.get_diff(storage_end_date, port_storage_start_date) + 1;
        } else {
            row.storage_days_accumulated = 0;
        }
    }

    frm.refresh_field('container_details');
}

// --- General cargo logic with to_be_returned check ---
function calculate_general_dnd_storage(frm, cdt, cdn) {
    const row = locals[cdt || 'General Cargo Details'][cdn];
    const { discharge_date, dnd_free_days, port_free_days } = frm.doc;
    const today = frappe.datetime.get_today();

    // D&D
    if (discharge_date && dnd_free_days !== null && !isNaN(dnd_free_days)) {
        const last_free_day = dnd_free_days > 0
            ? frappe.datetime.add_days(discharge_date, dnd_free_days - 1)
            : frappe.datetime.add_days(discharge_date, -1);
        const dnd_start = frappe.datetime.add_days(last_free_day, 1);

        const dnd_end = row.to_be_returned
            ? row.gate_in_date || today
            : row.gate_out_date || today;

        if (frappe.datetime.obj_to_str(dnd_end) > frappe.datetime.obj_to_str(last_free_day)) {
            row.dnd_days_accumulated = frappe.datetime.get_diff(dnd_end, dnd_start) + 1;
        } else {
            row.dnd_days_accumulated = 0;
        }
    } else {
        row.dnd_days_accumulated = 0;
    }

    // Port Storage
    if (discharge_date && port_free_days !== null && !isNaN(port_free_days)) {
        const last_free_day = port_free_days > 0
            ? frappe.datetime.add_days(discharge_date, port_free_days - 1)
            : frappe.datetime.add_days(discharge_date, -1);
        const storage_start = frappe.datetime.add_days(last_free_day, 1);
        const storage_end = row.gate_out_date || today;

        if (frappe.datetime.obj_to_str(storage_end) >= frappe.datetime.obj_to_str(storage_start)) {
            row.storage_days_accumulated = frappe.datetime.get_diff(storage_end, storage_start) + 1;
        } else {
            row.storage_days_accumulated = 0;
        }
    } else {
        row.storage_days_accumulated = 0;
    }

    frm.refresh_field('general_cargo_details');
}

// --- Aggregate totals for parent display ---
function update_total_dnd_days(frm) {
    let total = 0;
    (frm.doc.container_details || []).forEach(row => {
        total += parseInt(row.dnd_days_accumulated || 0);
    });
    (frm.doc.general_cargo_details || []).forEach(row => {
        total += parseInt(row.dnd_days_accumulated || 0);
    });
    frm.set_value('total_dnd_days', total);
}

function update_total_storage_days(frm) {
    let total = 0;
    (frm.doc.container_details || []).forEach(row => {
        total += parseInt(row.storage_days_accumulated || 0);
    });
    (frm.doc.general_cargo_details || []).forEach(row => {
        total += parseInt(row.storage_days_accumulated || 0);
    });
    frm.set_value('total_storage_days', total);
}

///////////////////////////////////////////////////////////////////////////////
// ========================================
// UPDATE CONTAINER & PACKAGE COUNT SUMMARY
// ========================================
// This block calculates:
// - A summary of container types from the Container Details table (e.g. "4 x 20SD, 2 x 40HC")
// - A count of rows from the General Cargo Details table (e.g. "3 x Packages")
// The results are set on the parent fields: container_count and packages_count
// ========================================

function update_container_and_package_counts(frm) {
    let container_summary = {};
    let container_text = "";
    let total_containers = 0;

    // Count container types
    (frm.doc.container_details || []).forEach(row => {
        if (row.container_type) {
            container_summary[row.container_type] = (container_summary[row.container_type] || 0) + 1;
            total_containers++;
        }
    });

    // Format like "4 x 20SD, 2 x 40HC"
    let parts = [];
    for (let type in container_summary) {
        parts.push(`${container_summary[type]} x ${type}`);
    }
    if (parts.length) {
        container_text = parts.join(", ");
    }

    // Count general cargo packages
    let general_count = frm.doc.general_cargo_details?.length || 0;
    let package_text = general_count ? `${general_count} x Packages` : "";

    // Set values
    frm.set_value('container_count', container_text);
    frm.set_value('packages_count', package_text);
}

// Triggers when rows are added or edited
frappe.ui.form.on('Container Details', {
    container_type: update_container_and_package_counts,
    container_number: update_container_and_package_counts,
    container_details_remove: update_container_and_package_counts
});

frappe.ui.form.on('General Cargo Details', {
    item_description: update_container_and_package_counts,
    general_cargo_details_remove: update_container_and_package_counts
});

frappe.ui.form.on('Clearing Job', {
    onload: function(frm) {
        update_container_and_package_counts(frm);
    },
    refresh: function(frm) {
        update_container_and_package_counts(frm);
    }
});


///////////////////////////////////////////////////////////////////////////

// ========================================
// VALIDATE ISO 6346 CONTAINER NUMBER + NO DUPLICATES
// ========================================

frappe.ui.form.on('Container Details', {
    container_number: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const number = (row.container_number || "").toUpperCase().trim();

        // Basic ISO format: 4 letters + 7 digits
        if (number.length !== 11 || !/^[A-Z]{4}\d{7}$/.test(number)) {
            frappe.msgprint(`Container number "${number}" is not a valid Container Number.`);
            row.container_number = "";
            frm.refresh_field("container_details");
            return;
        }

        // Check digit validation
        if (!is_valid_iso_container_number(number)) {
            frappe.msgprint(`Container number "${number}" has an invalid check digit.`);
            row.container_number = "";
            frm.refresh_field("container_details");
            return;
        }

        // Duplicate check
        const existing = (frm.doc.container_details || []).filter(r =>
            r.name !== row.name && r.container_number === number
        );
        if (existing.length > 0) {
            frappe.msgprint(`Container number "${number}" is already entered in another row.`);
            row.container_number = "";
            frm.refresh_field("container_details");
            return;
        }

        // Set back formatted number (uppercase)
        row.container_number = number;
        frm.refresh_field("container_details");
    }
});

// ISO 6346 Check Digit Validator
function is_valid_iso_container_number(container_number) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const weights = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512];
    let sum = 0;

    for (let i = 0; i < 10; i++) {
        const char = container_number[i];
        let value;

        if (i < 4) {
            const code = letters.indexOf(char);
            if (code === -1) return false;
            value = (code + 10) + Math.floor((code + 10) / 11);
        } else {
            value = parseInt(char);
        }

        sum += value * weights[i];
    }

    let check_digit = sum % 11;
    if (check_digit === 10) check_digit = 0;

    return parseInt(container_number[10]) === check_digit;
}


////////////////////////////////////////////////////////////////////////