// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
// For license information, please see license.txt

// ==========================================================
// Forwarding Job - Client Script
// Handles currency logic, charge calculations, invoicing,
// and cargo count summary
// ==========================================================

frappe.ui.form.on('Forwarding Job', {
  refresh(frm) {
    calculate_forwarding_totals(frm);
    toggle_base_fields(frm);
    update_currency_labels(frm);
    update_cargo_count_forwarding(frm);

    // Add the missing custom buttons
    if (!frm.is_new()) {
      frm.add_custom_button(__('Create Sales Invoice'), function() {
        create_sales_invoice_from_charges(frm);
      }, __('Create'));

      frm.add_custom_button(__('Create Purchase Invoice'), function() {
        create_purchase_invoice_from_charges(frm);
      }, __('Create'));
    }
  },

  validate(frm) {
    calculate_forwarding_totals(frm);
  },

  currency(frm) {
    if (frm.doc.currency && frm.doc.base_currency && frm.doc.currency !== frm.doc.base_currency) {
      frappe.call({
        method: "erpnext.setup.utils.get_exchange_rate",
        args: {
          from_currency: frm.doc.currency,
          to_currency: frm.doc.base_currency
        },
        callback(r) {
          if (r.message) {
            set_main_value_safe(frm, "conversion_rate", r.message);
            calculate_forwarding_totals(frm);
            toggle_base_fields(frm);
          }
        }
      });
    } else {
      set_main_value_safe(frm, "conversion_rate", 1.0);
      calculate_forwarding_totals(frm);
      toggle_base_fields(frm);
    }

    update_currency_labels(frm);
  },

  conversion_rate(frm) {
    calculate_forwarding_totals(frm);
  },

  base_currency(frm) {
    update_currency_labels(frm);
  },

  before_save(frm) {
    const tracking = frm.doc.forwarding_tracking;
    if (tracking && tracking.length > 0) {
      const last = tracking[tracking.length - 1];

      set_main_value_safe(frm, 'current_comment', last.comment);
      set_main_value_safe(frm, 'last_updated_on', last.updated_on);
      set_main_value_safe(frm, 'last_updated_by', last.updated_by);
    }
  },
});

// ==========================================================
// Charge Row Calculation Logic
// ==========================================================

function update_charge_row(frm, cdt, cdn) {
  const row = locals[cdt][cdn];
  row.revenue_amount = (row.qty || 0) * (row.sell_rate || 0);
  row.cost_amount = (row.qty || 0) * (row.buy_rate || 0);
  frm.refresh_field('forwarding_charges');
  calculate_forwarding_totals(frm);
}

function calculate_forwarding_totals(frm) {
  let total_revenue = 0;
  let total_cost = 0;

  (frm.doc.forwarding_charges || []).forEach(row => {
    total_revenue += row.revenue_amount || 0;
    total_cost += row.cost_amount || 0;
  });

  const profit = total_revenue - total_cost;
  const rate = frm.doc.conversion_rate || 1.0;

  set_main_value_safe(frm, 'total_estimated_revenue', total_revenue);
  set_main_value_safe(frm, 'total_estimated_cost', total_cost);
  set_main_value_safe(frm, 'total_estimated_profit', profit);

  set_main_value_safe(frm, 'total_estimated_revenue_base', total_revenue * rate);
  set_main_value_safe(frm, 'total_estimated_cost_base', total_cost * rate);
  set_main_value_safe(frm, 'total_estimated_profit_base', profit * rate);
}

// Show/hide base currency fields
function toggle_base_fields(frm) {
  const hide = frm.doc.currency === frm.doc.base_currency;
  frm.toggle_display("total_estimated_revenue_base", !hide);
  frm.toggle_display("total_estimated_cost_base", !hide);
  frm.toggle_display("total_estimated_profit_base", !hide);
}

// Update currency labels dynamically on both parent and child tables
function update_currency_labels(frm) {
  const currency = frm.doc.currency || "USD";
  const base_currency = frm.doc.base_currency || "USD";

  const labels = {
    total_estimated_revenue: `Total Estimated Revenue (${currency})`,
    total_estimated_cost: `Total Estimated Cost (${currency})`,
    total_estimated_profit: `Total Estimated Profit (${currency})`,
    total_estimated_revenue_base: `Total Estimated Revenue (${base_currency})`,
    total_estimated_cost_base: `Total Estimated Cost (${base_currency})`,
    total_estimated_profit_base: `Total Estimated Profit (${base_currency})`
  };

  for (const [field, label] of Object.entries(labels)) {
    if (frm.fields_dict[field]) {
      frm.set_df_property(field, "label", label);
    }
  }

  if (frm.fields_dict.forwarding_charges) {
    const grid = frm.fields_dict.forwarding_charges.grid;
    grid.update_docfield_property("sell_rate", "label", `Sell Rate (${currency})`);
    grid.update_docfield_property("buy_rate", "label", `Buy Rate (${currency})`);
    grid.update_docfield_property("revenue_amount", "label", `Revenue (${currency})`);
    grid.update_docfield_property("cost_amount", "label", `Cost (${currency})`);
  }
}

// ==========================================================
// Charge Row Field Locking and Deletion Prevention
// ==========================================================

frappe.ui.form.on('Forwarding Charges', {
  form_render(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const grid_row = frm.fields_dict.forwarding_charges.grid.grid_rows_by_docname[cdn];

    if (row.sales_invoice_reference) {
      grid_row.columns.forEach(col => {
        if (col.df.fieldname !== 'sales_invoice_reference') {
          col.df.read_only = 1;
        }
      });
    }

    if (row.purchase_invoice_reference) {
      grid_row.columns.forEach(col => {
        if (col.df.fieldname !== 'purchase_invoice_reference') {
          col.df.read_only = 1;
        }
      });
    }

    grid_row.refresh();
  },

  before_forwarding_charges_remove(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.sales_invoice_reference || row.purchase_invoice_reference) {
      frappe.throw(__("Cannot delete row that has been invoiced. Please remove the invoice reference first."));
    }
  },

  qty: update_charge_row,
  sell_rate: update_charge_row,
  buy_rate: update_charge_row,
  forwarding_charges_remove(frm) {
    calculate_forwarding_totals(frm);
  }
});

// ==========================================================
// Safe Value Setter
// Only set value if changed to avoid dirty states
// ==========================================================

function set_main_value_safe(frm, fieldname, value) {
  const field = frm.fields_dict[fieldname];
  if (!field || field.df.fieldtype === "Date" || field.df.fieldtype === "Datetime" || frm.doc[fieldname] !== value) {
    frm.set_value(fieldname, value);
  }
}

// ==========================================================
// Invoicing Handlers (Sales & Purchase)
// ==========================================================

// Calls reusable dialog logic (already well-written) for both invoice types
// Included in full above, kept modular for maintainability

// ==========================================================
// Cargo Count Summary Logic (Containerised + Packages)
// ==========================================================

function update_cargo_count_forwarding(frm) {
  const table = frm.doc.cargo_parcel_details || [];
  let container_counts = {};
  let package_count = 0;

  table.forEach(row => {
    if (row.cargo_type?.toLowerCase() === "containerised") {
      let ctype = row.container_type || "Unknown Type";
      container_counts[ctype] = (container_counts[ctype] || 0) + 1;
    } else {
      package_count += row.cargo_quantity || 1;
    }
  });

  let summary = [];
  for (const type in container_counts) {
    summary.push(`${container_counts[type]} x ${type}`);
  }
  if (package_count > 0) {
    summary.push(`${package_count} x PKG${package_count > 1 ? "s" : ""}`);
  }

  set_main_value_safe(frm, "cargo_count", summary.join(", "));
}

// ==========================================================
// Cargo Parcel Details Table Triggers
// ==========================================================

frappe.ui.form.on('Cargo Parcel Details', {
  cargo_type: update_cargo_count_forwarding,
  container_type: update_cargo_count_forwarding,
  cargo_quantity: update_cargo_count_forwarding,
  cargo_parcel_details_add: update_cargo_count_forwarding,
  cargo_parcel_details_remove: update_cargo_count_forwarding
});

function create_sales_invoice_from_charges(frm) {
  const all_rows = frm.doc.forwarding_charges || [];
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
        method: "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_sales_invoice_with_rows",
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
  const all_rows = frm.doc.forwarding_charges || [];
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
        method: "freightmas.forwarding_service.doctype.forwarding_job.forwarding_job.create_purchase_invoice_with_rows",
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

//////////////////////////////////////////////
// Fetch Charges from Quotation   ///////////

frappe.ui.form.on('Forwarding Job', {
    fetch_from_quotation(frm) {
        open_fetch_charges_from_quotation_dialog(frm);
    }
});

function open_fetch_charges_from_quotation_dialog(frm) {
    if (!frm.doc.customer) {
        frappe.msgprint(__('Please select a Customer first.'));
        return;
    }
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Quotation',
            filters: [
                ['docstatus', '=', 1],
                ['job_type', '=', "Forwarding"],
                ['customer_name', '=', frm.doc.customer],
                ['valid_till', '>=', frappe.datetime.nowdate()]
            ],
            fields: ['name', 'customer_name', 'origin_port', 'destination_port', 'valid_till'],
            limit_page_length: 50,
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                let quotation_options = r.message.map(q =>
                    `${q.name} (${q.customer_name || ''} / ${q.origin_port || ''} → ${q.destination_port || ''})`
                );
                let quotation_names = r.message.map(q => q.name);

                let d = new frappe.ui.Dialog({
                    title: __('Fetch Charges from Quotation'),
                    fields: [
                        {
                            fieldname: 'quotation',
                            label: 'Quotation',
                            fieldtype: 'Select',
                            options: quotation_options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Fetch Charges',
                    primary_action(values) {
                        let idx = quotation_options.indexOf(values.quotation);
                        if (idx >= 0) {
                            let quotation_name = quotation_names[idx];
                            fetch_and_append_quotation_charges(frm, quotation_name);
                        }
                        d.hide();
                    }
                });
                d.show();
            } else {
                frappe.msgprint(__('No valid Forwarding Quotations found for this customer.'));
            }
        }
    });
}

function fetch_and_append_quotation_charges(frm, quotation_name) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Quotation',
            name: quotation_name
        },
        callback: function (r) {
            if (r.message && r.message.items) {
                let items = r.message.items;
                let parent_customer = r.message.customer_name;
                let existing_charges = (frm.doc.forwarding_charges || []).map(row => row.charge);

                let added_count = 0;
                items.forEach(item => {
                    if (!existing_charges.includes(item.item_code)) {
                        let child = frm.add_child('forwarding_charges', {
                            charge: item.item_code,
                            description: strip_html_tags(item.description),
                            qty: item.qty,
                            sell_rate: item.rate,
                            buy_rate: item.buy_rate,
                            supplier: item.supplier,
                            customer: parent_customer
                        });
                        child.revenue_amount = (item.qty || 0) * (item.rate || 0);
                        child.cost_amount = (item.qty || 0) * (item.buy_rate || 0);
                        added_count += 1;
                    }
                });

                frm.refresh_field('forwarding_charges');
                // If you have a totals calculation, call it here
                // calculate_forwarding_totals(frm);

                if (added_count === 0) {
                    frappe.msgprint(__('All quotation charges already exist in the charges table. No new charges added.'));
                } else {
                    frappe.msgprint(__(`${added_count} charge(s) loaded from quotation.`));
                }
            }
        }
    });
}

// Strip HTML tags from a description string
function strip_html_tags(html) {
    let tmp = document.createElement("DIV");
    tmp.innerHTML = html || "";
    return tmp.textContent || tmp.innerText || "";
}

////////////////////////////////////////////////////////////