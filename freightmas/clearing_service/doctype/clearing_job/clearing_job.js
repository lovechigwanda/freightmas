// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// ====================================================
// This script controls the visibility and validation of fields in the Clearing Job form
// based on the selected BL Type and other conditions.
// ====================================================
frappe.ui.form.on('Clearing Job', {
  refresh: function(frm) {
    toggle_directional_fields(frm);
    toggle_bl_fields(frm);
    toggle_milestone_dates(frm);
    render_progress_dial_and_theme_chips(frm);
    calculate_clearing_totals(frm);
    toggle_base_fields(frm);
    update_currency_labels(frm);
  },

  shipping_line: function(frm) {
    if (frm.doc.shipping_line) {
      frappe.db.get_doc('Shipping Line', frm.doc.shipping_line)
        .then(doc => {
          if (doc.free_days_import && frm.doc.direction === "Import") {
            frm.set_value('dnd_free_days', doc.free_days_import);
            frm.set_value('port_free_days', doc.free_days_import);
          }
          if (doc.free_days_export && frm.doc.direction === "Export") {
            frm.set_value('dnd_free_days', doc.free_days_export);
            frm.set_value('port_free_days', doc.free_days_export);
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
    calculate_clearing_totals(frm);
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
            if (frm.doc.conversion_rate !== r.message) {
              frm.set_value("conversion_rate", r.message);
            }
            calculate_clearing_totals(frm);
            toggle_base_fields(frm);
          }
        }
      });
    } else {
      if (frm.doc.conversion_rate !== 1.0) {
        frm.set_value("conversion_rate", 1.0);
      }
      calculate_clearing_totals(frm);
      toggle_base_fields(frm);
    }
    update_currency_labels(frm);
  },

  conversion_rate: function(frm) {
    calculate_clearing_totals(frm);
  },

  base_currency: function(frm) {
    update_currency_labels(frm);
  }
});

// ---------- Helper Functions -------------

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
    "do_received_date", "port_release_confirmed_date", "sl_invoice_received_date", "sl_invoice_payment_date",
    "discharge_date"
  ];

  // Export-specific fields
  const export_checkboxes = [
    "is_booking_confirmed", "is_clearing_for_shipment_done", "is_loaded_on_vessel", "is_vessel_sailed"
  ];
  const export_dates = [
    "booking_confirmation_date", "shipment_cleared_date", "loaded_on_vessel_date", "vessel_sailed_date",
    "vessel_loading_date"
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

// --- CALCULATIONS LOGIC (With Multi-Currency & Base Fields Hidden) ---
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

  if (frm.doc.total_estimated_revenue !== total_revenue)
    frm.set_value('total_estimated_revenue', total_revenue);
  if (frm.doc.total_estimated_cost !== total_cost)
    frm.set_value('total_estimated_cost', total_cost);
  if (frm.doc.total_estimated_profit !== profit)
    frm.set_value('total_estimated_profit', profit);

  const revenue_base = total_revenue * rate;
  const cost_base = total_cost * rate;
  const profit_base = profit * rate;

  if (frm.doc.total_estimated_revenue_base !== revenue_base)
    frm.set_value('total_estimated_revenue_base', revenue_base);
  if (frm.doc.total_estimated_cost_base !== cost_base)
    frm.set_value('total_estimated_cost_base', cost_base);
  if (frm.doc.total_estimated_profit_base !== profit_base)
    frm.set_value('total_estimated_profit_base', profit_base);
}

function toggle_base_fields(frm) {
  const is_same_currency = frm.doc.currency === frm.doc.base_currency;

  frm.toggle_display("total_estimated_revenue_base", !is_same_currency);
  frm.toggle_display("total_estimated_cost_base", !is_same_currency);
  frm.toggle_display("total_estimated_profit_base", !is_same_currency);
}

// ---- DYNAMIC CURRENCY LABELS ----
function update_currency_labels(frm) {
  const currency = frm.doc.currency || "USD";
  const base_currency = frm.doc.base_currency || "USD";

  // --- Parent Fields ---
  const label_map = {
    "total_estimated_revenue": `Total Estimated Revenue (${currency})`,
    "total_estimated_cost": `Total Estimated Cost (${currency})`,
    "total_estimated_profit": `Total Estimated Profit (${currency})`,
    "total_estimated_revenue_base": `Total Estimated Revenue (${base_currency})`,
    "total_estimated_cost_base": `Total Estimated Cost (${base_currency})`,
    "total_estimated_profit_base": `Total Estimated Profit (${base_currency})`
  };

  for (const [fieldname, label] of Object.entries(label_map)) {
    if (frm.fields_dict[fieldname]) {
      frm.fields_dict[fieldname].df.label = label;
      frm.refresh_field(fieldname);
    }
  }

  // --- Child Table Labels (safe) ---
  if (frm.fields_dict.clearing_charges) {
    frm.fields_dict.clearing_charges.grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
    frm.fields_dict.clearing_charges.grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
    frm.fields_dict.clearing_charges.grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    frm.fields_dict.clearing_charges.grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
  }
}

// --- FIELD LOCKING + DELETION PREVENTION FOR INVOICED CHARGES ---
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
    const row = locals[cdt][cdn];
    if (row.sales_invoice_reference || row.purchase_invoice_reference) {
      frappe.throw(__("You cannot delete a charge that is already invoiced."));
    }
  },

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

// --- MILESTONE SECTION FROM LAST ROW OF CLEARING TRACKING TABLE ---
frappe.ui.form.on('Clearing Job', {
  before_save: function(frm) {
    const tracking = frm.doc.clearing_tracking;
    if (tracking && tracking.length > 0) {
      const last = tracking[tracking.length - 1];

      if (frm.doc.current_comment !== last.comment)
        frm.set_value('current_comment', last.comment);
      if (frm.doc.last_updated_on !== last.updated_on)
        frm.set_value('last_updated_on', last.updated_on);
      if (frm.doc.last_updated_by !== last.updated_by)
        frm.set_value('last_updated_by', last.updated_by);
    }
  }
});

// --- Milestone Tracker UI Refresh Triggers ---
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

// --- Sales Invoice Button ---
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

// --- Purchase Invoice Button ---
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


////////////////////////////////////////////////////
// ==========================================================
// LOAD CHARGES FROM TEMPLATE - Clearing Job Doctype//

// This block allows users to quickly populate the charges table
// with pre-defined charge templates, saving time and ensuring
// consistency across jobs. It includes quantity control, duplicate
// prevention, automatic totals, and full user feedback.
//
// Requirements handled:
// - Form button triggers dialog for template/quantity selection
// - Filters templates by direction & shipping line
// - Prevents duplicate charges (by charge name)
// - Sets all fields as per mapping, quantity included
// - Calculates row and total amounts
// - User sees result messages
// ==========================================================

frappe.ui.form.on('Clearing Job', {
  // This event is triggered when the button field (placed above the charges table) is clicked
  load_charges_from_template(frm) {
    open_charges_template_dialog(frm);
  }
});

/**
 * Opens a dialog to select a charge template and quantity.
 * Filters templates by current job direction and shipping line.
 * On selection, triggers loading/appending charges.
 */
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
        // Build human-readable template options for the select field
        let template_options = r.message.map(tpl =>
          `${tpl.name} (${tpl.shipping_line || ''} / ${tpl.container_type || ''} / ${tpl.direction})`
        );
        let template_names = r.message.map(tpl => tpl.name);

        // Show dialog to select template and quantity
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

/**
 * Appends charges from the selected template to the charges child table.
 * Prevents duplicate charge entries (by charge name).
 * Sets all required fields and computes revenue/cost per row.
 * Triggers recalculation of parent totals.
 *
 * @param {Object} frm - Frappe form object
 * @param {string} template_name - Selected template document name
 * @param {number} quantity - Quantity to apply to all rows
 */
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
        // Build list of existing charges to prevent duplicates
        let existing_charges = (frm.doc.clearing_charges || []).map(row => row.charge);

        let added_count = 0;
        items.forEach(row => {
          // Prevent duplicate charges by charge name
          if (!existing_charges.includes(row.charge)) {
            let child = frm.add_child('clearing_charges', {
              charge: row.charge,
              sell_rate: row.sell_rate,
              buy_rate: row.buy_rate,
              supplier: row.supplier,
              customer: parent_customer,
              qty: quantity // User-specified quantity
            });
            // Calculate revenue and cost per row
            child.revenue_amount = (quantity || 0) * (row.sell_rate || 0);
            child.cost_amount = (quantity || 0) * (row.buy_rate || 0);
            added_count += 1;
          }
        });

        frm.refresh_field('clearing_charges');
        calculate_clearing_totals(frm); // Always recalculate totals

        // Give user feedback
        if (added_count === 0) {
          frappe.msgprint(__('All template charges already exist in the charges table. No new charges added.'));
        } else {
          frappe.msgprint(__(`${added_count} charge(s) loaded from template.`));
        }
      }
    }
  });
}

// ==========================================================
// CARGO PACKAGE COUNT SUMMARY LOGIC
// ----------------------------------------------------------
// This section automatically updates the 'cargo_count' field
// with a summary like "3 x 40SD, 2 x Packages" whenever the
// Cargo Package Details child table is changed (add, remove,
// or edit). It counts each containerised row by type and
// sums up general cargo packages by quantity.
// ==========================================================

function set_value_safe(frm, fieldname, value) {
    // Always set for date fields to ensure triggers fire
    frm.set_value(fieldname, value);
}

function update_cargo_count(frm) {
    let table = frm.doc.cargo_package_details || [];
    let container_counts = {};
    let package_count = 0;

    table.forEach(row => {
        if (row.cargo_type && row.cargo_type.toLowerCase() === "containerised") {
            let ctype = row.container_type || "Unknown Type";
            container_counts[ctype] = (container_counts[ctype] || 0) + 1;
        } else {
            // Use cargo_quantity if present, else count as 1 per row
            package_count += row.cargo_quantity ? row.cargo_quantity : 1;
        }
    });

    let summary = [];
    Object.keys(container_counts).forEach(type => {
        summary.push(`${container_counts[type]} x ${type}`);
    });
    if (package_count > 0) {
        summary.push(`${package_count} x Package${package_count > 1 ? "s" : ""}`);
    }
    set_value_safe(frm, "cargo_count", summary.join(", "));
}

// Main form triggers
frappe.ui.form.on('Clearing Job', {
    refresh(frm) { update_cargo_count(frm); }
});

// Child table triggers
frappe.ui.form.on('Cargo Package Details', {
    cargo_type: update_cargo_count,
    container_type: update_cargo_count,
    cargo_quantity: update_cargo_count,
    cargo_package_details_add: function(frm) { update_cargo_count(frm); },
    cargo_package_details_remove: function(frm) { update_cargo_count(frm); }
});

// --- DND AND STORAGE DATE LOGIC ---
function update_dnd_and_storage_dates(frm) {
    const discharge_date = frm.doc.discharge_date;
    const is_discharged_from_vessel = frm.doc.is_discharged_from_vessel;
    const dnd_days = parseInt(frm.doc.dnd_free_days) || 0;
    const port_days = parseInt(frm.doc.port_free_days) || 0;

    if (discharge_date && is_discharged_from_vessel) {
        const dnd_start = frappe.datetime.add_days(discharge_date, dnd_days + 1);
        const storage_start = frappe.datetime.add_days(discharge_date, port_days + 1);

        set_value_safe(frm, "dnd_start_date", dnd_start);
        set_value_safe(frm, "storage_start_date", storage_start);
    } else {
        set_value_safe(frm, "dnd_start_date", null);
        set_value_safe(frm, "storage_start_date", null);
        // If is_discharged_from_vessel is cleared, also clear discharge_date
        if (!is_discharged_from_vessel && discharge_date) {
            set_value_safe(frm, "discharge_date", null);
        }
    }
}

// Triggers for the relevant fields
frappe.ui.form.on('Clearing Job', {
    discharge_date: update_dnd_and_storage_dates,
    dnd_free_days: update_dnd_and_storage_dates,
    port_free_days: update_dnd_and_storage_dates,
    is_discharged_from_vessel: update_dnd_and_storage_dates
});

