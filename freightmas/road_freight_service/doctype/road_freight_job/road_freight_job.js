// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// For license information, please see license.txt

frappe.ui.form.on('Road Freight Job', {
  refresh(frm) {
    update_trucks_confirmed(frm);
    calculate_freight_totals(frm);
    toggle_base_fields(frm);
    update_currency_labels(frm);

    if (!frm.is_new()) {
      frm.add_custom_button(__('Create Sales Invoice'), function () {
        create_sales_invoice_from_charges(frm);
      }, __('Create'));

      frm.add_custom_button(__('Create Purchase Invoice'), function () {
        create_purchase_invoice_from_charges(frm);
      }, __('Create'));
    }
  },

  onload_post_render(frm) {
    update_trucks_confirmed(frm);
  },

  validate(frm) {
    calculate_freight_totals(frm);
  },

  currency(frm) {
    if (frm.doc.currency && frm.doc.base_currency && frm.doc.currency !== frm.doc.base_currency) {
      frappe.call({
        method: "erpnext.setup.utils.get_exchange_rate",
        args: {
          from_currency: frm.doc.currency,
          to_currency: frm.doc.base_currency
        },
        callback: function (r) {
          if (r.message) {
            set_main_value_safe(frm, "conversion_rate", r.message);
            calculate_freight_totals(frm);
            toggle_base_fields(frm);
          }
        }
      });
    } else {
      set_main_value_safe(frm, "conversion_rate", 1.0);
      calculate_freight_totals(frm);
      toggle_base_fields(frm);
    }

    update_currency_labels(frm);
  },

  conversion_rate: calculate_freight_totals,
  base_currency: update_currency_labels,

  // Handle custom Button field
  copy_charges_from_truck_loading(frm) {
    copy_charges_from_truck_loading(frm);
  }
});

// -------------------- Truck Loading Table --------------------

frappe.ui.form.on('Truck Loading Details', {
  truck_loading_details_add: update_trucks_confirmed,
  truck_loading_details_remove: update_trucks_confirmed
});

// -------------------- Charges Table --------------------

frappe.ui.form.on('Road Freight Charges', {
  form_render(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const grid_row = frm.fields_dict.road_freight_charges.grid.grid_rows_by_docname[cdn];

    if (row.sales_invoice_reference) {
      grid_row.columns.forEach(col => {
        if (col.df.fieldname !== 'sales_invoice_reference') col.df.read_only = 1;
      });
    }

    if (row.purchase_invoice_reference) {
      grid_row.columns.forEach(col => {
        if (col.df.fieldname !== 'purchase_invoice_reference') col.df.read_only = 1;
      });
    }

    grid_row.refresh();
  },

  before_road_freight_charges_remove(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.sales_invoice_reference || row.purchase_invoice_reference) {
      frappe.throw(__("Cannot delete a charge that is already invoiced."));
    }
  },

  qty: update_charge_row,
  sell_rate: update_charge_row,
  buy_rate: update_charge_row,
  road_freight_charges_remove: calculate_freight_totals
});

// -------------------- Utility Functions --------------------

function update_trucks_confirmed(frm) {
  const count = (frm.doc.truck_loading_details || []).length;
  set_main_value_safe(frm, 'trucks_confirmed', count);
}

function update_charge_row(frm, cdt, cdn) {
  const row = locals[cdt][cdn];
  row.revenue_amount = (row.qty || 0) * (row.sell_rate || 0);
  row.cost_amount = (row.qty || 0) * (row.buy_rate || 0);
  frm.refresh_field('road_freight_charges');
  calculate_freight_totals(frm);
}

function calculate_freight_totals(frm) {
  let total_revenue = 0, total_cost = 0;
  const rate = frm.doc.conversion_rate || 1.0;

  (frm.doc.road_freight_charges || []).forEach(row => {
    total_revenue += row.revenue_amount || 0;
    total_cost += row.cost_amount || 0;
  });

  const profit = total_revenue - total_cost;

  set_main_value_safe(frm, 'total_estimated_revenue', total_revenue);
  set_main_value_safe(frm, 'total_estimated_cost', total_cost);
  set_main_value_safe(frm, 'total_estimated_profit', profit);

  set_main_value_safe(frm, 'total_estimated_revenue_base', total_revenue * rate);
  set_main_value_safe(frm, 'total_estimated_cost_base', total_cost * rate);
  set_main_value_safe(frm, 'total_estimated_profit_base', profit * rate);
}

function toggle_base_fields(frm) {
  const same = frm.doc.currency === frm.doc.base_currency;
  frm.toggle_display("total_estimated_revenue_base", !same);
  frm.toggle_display("total_estimated_cost_base", !same);
  frm.toggle_display("total_estimated_profit_base", !same);
}

function update_currency_labels(frm) {
  const currency = frm.doc.currency || "USD";
  const base = frm.doc.base_currency || "USD";

  const label_map = {
    "total_estimated_revenue": `Total Estimated Revenue (${currency})`,
    "total_estimated_cost": `Total Estimated Cost (${currency})`,
    "total_estimated_profit": `Total Estimated Profit (${currency})`,
    "total_estimated_revenue_base": `Total Estimated Revenue (${base})`,
    "total_estimated_cost_base": `Total Estimated Cost (${base})`,
    "total_estimated_profit_base": `Total Estimated Profit (${base})`
  };

  for (const [field, label] of Object.entries(label_map)) {
    if (frm.fields_dict[field]) {
      frm.set_df_property(field, "label", label);
    }
  }

  const grid = frm.fields_dict.road_freight_charges?.grid;
  if (grid) {
    grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
    grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
    grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
  }
}

function set_main_value_safe(frm, fieldname, value) {
  const field = frm.fields_dict[fieldname];
  if (!field) return;
  if (field.df.fieldtype === "Date" || field.df.fieldtype === "Datetime") {
    value = value ? frappe.datetime.str_to_obj(value) : null;
  }
  if (frm.doc[fieldname] !== value) {
    frm.set_value(fieldname, value);
  }
}

// -------------------- Main Charge Creation Logic --------------------

function copy_charges_from_truck_loading(frm) {
  const customer = frm.doc.customer;
  if (!customer) {
    frappe.msgprint(__('Please select a customer before copying charges.'));
    return;
  }

  const loading_rows = frm.doc.truck_loading_details || [];
  const pol = frm.doc.port_of_loading || '';
  const pod = frm.doc.port_of_discharge || '';
  const drop = frm.doc.empty_drop_off_at || '';
  const cargo = frm.doc.cargo_description || '';

  let added_count = 0;

  loading_rows.forEach(row => {
    if (row.copied_to_charge) return; // Skip if already copied

    const charge = row.service_charge;
    const horse = row.horse || '';
    const supplier = row.transporter;

    const description = `${charge} Truck ${horse} ${pol} > ${pod} (drop ${drop}) ${cargo}`.trim();

    const new_row = frm.add_child('road_freight_charges', {
      charge: charge,
      description: description,
      qty: row.cargo_quantity || 1,
      sell_rate: row.selling_rate || row.client_rate || 0,
      buy_rate: row.buying_rate || row.transporter_rate || 0,
      customer: customer,
      supplier: supplier
    });

    new_row.revenue_amount = (new_row.qty || 0) * (new_row.sell_rate || 0);
    new_row.cost_amount = (new_row.qty || 0) * (new_row.buy_rate || 0);

    // ✅ Mark as copied
    row.copied_to_charge = 1;
    added_count++;
  });

  frm.refresh_field('truck_loading_details');
  frm.refresh_field('road_freight_charges');
  calculate_freight_totals(frm);

  if (added_count) {
    frappe.msgprint(__(`${added_count} new charge(s) added from Truck Loading.`));
  } else {
    frappe.msgprint(__('No new rows to copy — all are already marked as copied.'));
  }
}

function create_sales_invoice_from_charges(frm) {
  const all_rows = frm.doc.road_freight_charges || [];
  const eligible_rows = all_rows.filter(row => 
    row.sell_rate && row.customer && !row.sales_invoice_reference
  );

  if (!eligible_rows.length) {
    frappe.msgprint(__("No eligible charges found for invoicing."));
    return;
  }

  let selected_customer = eligible_rows[0].customer;

  const get_unique_customers = () => [...new Set(eligible_rows.map(r => r.customer))];

  const render_dialog_ui = (dialog, customer) => {
    const customers = get_unique_customers();
    const rows = customer ? eligible_rows.filter(r => r.customer === customer) : eligible_rows;

    const customer_filter = `
      <div style="margin-bottom: 15px;">
        <label for="customer-filter" style="font-weight: bold; margin-bottom: 5px; display: block;">Customer:</label>
        <select id="customer-filter" class="form-control" style="width: 100%;">
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
                <input type="checkbox" id="select-all-charges" title="Select All">
              </th>
              <th style="min-width: 150px;">Customer</th>
              <th style="min-width: 200px;">Description</th>
              <th style="width: 80px; text-align: right;">Qty</th>
              <th style="width: 100px; text-align: right;">Sell Rate</th>
              <th style="width: 100px; text-align: right;">Revenue</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr>
                <td style="text-align: center;">
                  <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
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

    // Customer filter change handler
    dialog.$wrapper.find('#customer-filter').on('change', function() {
      selected_customer = this.value;
      render_dialog_ui(dialog, selected_customer);
    });

    // Select all checkbox handler
    dialog.$wrapper.find('#select-all-charges').on('change', function() {
      const isChecked = this.checked;
      dialog.$wrapper.find('.charge-row-check').prop('checked', isChecked);
    });

    // Individual checkbox handler
    dialog.$wrapper.find('.charge-row-check').on('change', function() {
      const total = dialog.$wrapper.find('.charge-row-check').length;
      const checked = dialog.$wrapper.find('.charge-row-check:checked').length;
      dialog.$wrapper.find('#select-all-charges').prop('checked', total === checked);
    });
  };

  const dialog = new frappe.ui.Dialog({
    title: __('Select Charges for Sales Invoice'),
    size: 'large',
    fields: [
      {
        fieldtype: 'HTML',
        fieldname: 'charge_rows_html',
        options: ''
      }
    ],
    primary_action_label: __('Create Sales Invoice'),
    primary_action() {
      const selected = Array.from(
        dialog.$wrapper.find('.charge-row-check:checked')
      ).map(el => el.dataset.rowName);

      if (!selected.length) {
        frappe.msgprint(__("Please select at least one charge."));
        return;
      }

      const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
      const unique_customers = [...new Set(selected_rows.map(r => r.customer))];

      if (unique_customers.length > 1) {
        frappe.msgprint(__("You can only create an invoice for one customer at a time."));
        return;
      }

      frappe.call({
        method: "freightmas.road_freight_service.doctype.road_freight_job.road_freight_job.create_sales_invoice_with_rows",
        args: {
          docname: frm.doc.name,
          row_names: selected
        },
        callback(r) {
          if (r.message) {
            frappe.msgprint({
              title: __('Sales Invoice Created'),
              message: __('Sales Invoice {0} has been created successfully', [r.message]),
              indicator: 'green'
            });
            
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
}

function create_purchase_invoice_from_charges(frm) {
  const all_rows = frm.doc.road_freight_charges || [];
  const eligible_rows = all_rows.filter(row => 
    row.buy_rate && row.supplier && !row.purchase_invoice_reference
  );

  if (!eligible_rows.length) {
    frappe.msgprint(__("No eligible charges found for purchase invoicing."));
    return;
  }

  let selected_supplier = eligible_rows[0].supplier;

  const get_unique_suppliers = () => [...new Set(eligible_rows.map(r => r.supplier))];

  const render_dialog_ui = (dialog, supplier) => {
    const suppliers = get_unique_suppliers();
    const rows = supplier ? eligible_rows.filter(r => r.supplier === supplier) : eligible_rows;

    const supplier_filter = `
      <div style="margin-bottom: 15px;">
        <label for="supplier-filter" style="font-weight: bold; margin-bottom: 5px; display: block;">Supplier:</label>
        <select id="supplier-filter" class="form-control" style="width: 100%;">
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
                <input type="checkbox" id="select-all-charges" title="Select All">
              </th>
              <th style="min-width: 150px;">Supplier</th>
              <th style="min-width: 200px;">Description</th>
              <th style="width: 80px; text-align: right;">Qty</th>
              <th style="width: 100px; text-align: right;">Buy Rate</th>
              <th style="width: 100px; text-align: right;">Cost</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr>
                <td style="text-align: center;">
                  <input type="checkbox" class="charge-row-check" data-row-name="${row.name}">
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

    // Supplier filter change handler
    dialog.$wrapper.find('#supplier-filter').on('change', function() {
      selected_supplier = this.value;
      render_dialog_ui(dialog, selected_supplier);
    });

    // Select all checkbox handler
    dialog.$wrapper.find('#select-all-charges').on('change', function() {
      const isChecked = this.checked;
      dialog.$wrapper.find('.charge-row-check').prop('checked', isChecked);
    });

    // Individual checkbox handler
    dialog.$wrapper.find('.charge-row-check').on('change', function() {
      const total = dialog.$wrapper.find('.charge-row-check').length;
      const checked = dialog.$wrapper.find('.charge-row-check:checked').length;
      dialog.$wrapper.find('#select-all-charges').prop('checked', total === checked);
    });
  };

  const dialog = new frappe.ui.Dialog({
    title: __('Select Charges for Purchase Invoice'),
    size: 'large',
    fields: [
      {
        fieldtype: 'HTML',
        fieldname: 'charge_rows_html',
        options: ''
      }
    ],
    primary_action_label: __('Create Purchase Invoice'),
    primary_action() {
      const selected = Array.from(
        dialog.$wrapper.find('.charge-row-check:checked')
      ).map(el => el.dataset.rowName);

      if (!selected.length) {
        frappe.msgprint(__("Please select at least one charge."));
        return;
      }

      const selected_rows = eligible_rows.filter(r => selected.includes(r.name));
      const unique_suppliers = [...new Set(selected_rows.map(r => r.supplier))];

      if (unique_suppliers.length > 1) {
        frappe.msgprint(__("You can only create an invoice for one supplier at a time."));
        return;
      }

      frappe.call({
        method: "freightmas.road_freight_service.doctype.road_freight_job.road_freight_job.create_purchase_invoice_with_rows",
        args: {
          docname: frm.doc.name,
          row_names: selected
        },
        callback(r) {
          if (r.message) {
            frappe.msgprint({
              title: __('Purchase Invoice Created'),
              message: __('Purchase Invoice {0} has been created successfully', [r.message]),
              indicator: 'green'
            });
            
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
}


