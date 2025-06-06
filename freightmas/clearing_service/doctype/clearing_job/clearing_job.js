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
    update_cargo_count(frm);
    update_all_dnd_storage(frm);
    render_progress_dial_and_theme_chips(frm);
    calculate_clearing_totals(frm);
    toggle_base_fields(frm);
    update_currency_labels(frm);
  },

  shipping_line: function(frm) {
    if (frm.doc.shipping_line) {
      frappe.db.get_doc('Shipping Line', frm.doc.shipping_line)
        .then(doc => {
          // Set free days if present in Shipping Line
          if (doc.free_days_import && frm.doc.direction === "Import") {
            frm.set_value('dnd_free_days', doc.free_days_import);
            frm.set_value('port_free_days', doc.free_days_import); // If you have a separate field for port, use doc.free_days_export if needed
          }
          if (doc.free_days_export && frm.doc.direction === "Export") {
            frm.set_value('dnd_free_days', doc.free_days_export);
            frm.set_value('port_free_days', doc.free_days_export);
          }
        });
    }
  },

  direction: function(frm) {
    // Re-trigger shipping_line logic if direction changes
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

  onload: function(frm) {
    update_cargo_count(frm);
    update_all_dnd_storage(frm);
  },

  cargo_type: function(frm) {
    update_cargo_count(frm);
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
    "discharge_date" // show for import
  ];

  // Export-specific fields
  const export_checkboxes = [
    "is_booking_confirmed", "is_clearing_for_shipment_done", "is_loaded_on_vessel", "is_vessel_sailed"
  ];
  const export_dates = [
    "booking_confirmation_date", "shipment_cleared_date", "loaded_on_vessel_date", "vessel_sailed_date",
    "vessel_loading_date" // show for export
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

// --- D&D and Port Storage Days - AUTO CALCULATION ---
function get_base_date(doc) {
  return doc.direction === "Export" ? doc.vessel_loading_date : doc.discharge_date;
}

function update_all_dnd_storage(frm) {
  const base_date = get_base_date(frm.doc);
  const today = frappe.datetime.get_today();

  // Set DND start dates based on base date and free days
  if (base_date && !isNaN(frm.doc.dnd_free_days)) {
    const last_free_dnd_day = frm.doc.dnd_free_days > 0
      ? frappe.datetime.add_days(base_date, frm.doc.dnd_free_days - 1)
      : frappe.datetime.add_days(base_date, -1);
    if (frm.doc.last_free_dnd_day !== last_free_dnd_day) {
      frm.set_value('last_free_dnd_day', last_free_dnd_day);
    }
    const dnd_start_date = frappe.datetime.add_days(last_free_dnd_day, 1);
    if (frm.doc.dnd_start_date !== dnd_start_date) {
      frm.set_value('dnd_start_date', dnd_start_date);
    }
  } else {
    if (frm.doc.last_free_dnd_day) frm.set_value('last_free_dnd_day', null);
    if (frm.doc.dnd_start_date) frm.set_value('dnd_start_date', null);
  }

  // Set Port Storage start dates based on base date and free days
  if (base_date && !isNaN(frm.doc.port_free_days)) {
    const last_free_port_day = frm.doc.port_free_days > 0
      ? frappe.datetime.add_days(base_date, frm.doc.port_free_days - 1)
      : frappe.datetime.add_days(base_date, -1);
    if (frm.doc.port_last_free_day !== last_free_port_day) {
      frm.set_value('port_last_free_day', last_free_port_day);
    }
    const port_storage_start_date = frappe.datetime.add_days(last_free_port_day, 1);
    if (frm.doc.port_storage_start_date !== port_storage_start_date) {
      frm.set_value('port_storage_start_date', port_storage_start_date);
    }
  } else {
    if (frm.doc.port_last_free_day) frm.set_value('port_last_free_day', null);
    if (frm.doc.port_storage_start_date) frm.set_value('port_storage_start_date', null);
  }

  // Recalculate child rows if present
  (frm.doc.container_details || []).forEach(row => {
    calculate_container_dnd_and_storage(frm, null, row.name);
  });

  (frm.doc.general_cargo_details || []).forEach(row => {
    calculate_general_dnd_storage(frm, null, row.name);
  });

  // Always update totals and refresh UI
  update_total_dnd_days(frm);
  update_total_storage_days(frm);
  frm.refresh_field('container_details');
  frm.refresh_field('general_cargo_details');
}

function update_container_days(frm, cdt, cdn) {
  calculate_container_dnd_and_storage(frm, cdt, cdn);
  update_total_dnd_days(frm);
  update_total_storage_days(frm);
}

function update_general_days(frm, cdt, cdn) {
  calculate_general_dnd_storage(frm, cdt, cdn);
  update_total_dnd_days(frm);
  update_total_storage_days(frm);
}

function calculate_container_dnd_and_storage(frm, cdt, cdn) {
  const row = locals[cdt || "Container Details"][cdn];
  const base_date = get_base_date(frm.doc);
  const today = frappe.datetime.get_today();
  const direction = frm.doc.direction;

  const out_date = direction === "Export" ? row.pick_up_empty_date : row.gate_out_full_date;
  const return_date = direction === "Export" ? row.gate_in_full_date : row.gate_in_empty_date;

  // D&D Calculation
  if (base_date && !isNaN(frm.doc.dnd_free_days)) {
    const last_free_day = frm.doc.dnd_free_days > 0
      ? frappe.datetime.add_days(base_date, frm.doc.dnd_free_days - 1)
      : frappe.datetime.add_days(base_date, -1);
    const dnd_start = frappe.datetime.add_days(last_free_day, 1);
    const dnd_end = row.to_be_returned ? return_date || today : out_date || today;

    if (out_date === base_date) {
      row.dnd_days_accumulated = 0;
    } else if (frappe.datetime.obj_to_str(dnd_end) > frappe.datetime.obj_to_str(last_free_day)) {
      row.dnd_days_accumulated = frappe.datetime.get_diff(dnd_end, dnd_start) + 1;
    } else {
      row.dnd_days_accumulated = 0;
    }
  } else {
    row.dnd_days_accumulated = 0;
  }

  // Port Storage Calculation
  if (base_date && !isNaN(frm.doc.port_free_days)) {
    const last_free_day = frm.doc.port_free_days > 0
      ? frappe.datetime.add_days(base_date, frm.doc.port_free_days - 1)
      : frappe.datetime.add_days(base_date, -1);
    const storage_start = frappe.datetime.add_days(last_free_day, 1);
    const storage_end = out_date || today;

    if (frappe.datetime.obj_to_str(storage_end) >= frappe.datetime.obj_to_str(storage_start)) {
      row.storage_days_accumulated = frappe.datetime.get_diff(storage_end, storage_start) + 1;
    } else {
      row.storage_days_accumulated = 0;
    }
  } else {
    row.storage_days_accumulated = 0;
  }

  frm.refresh_field('container_details');
}

function calculate_general_dnd_storage(frm, cdt, cdn) {
  const row = locals[cdt || "General Cargo Details"][cdn];
  const base_date = get_base_date(frm.doc);
  const today = frappe.datetime.get_today();
  const direction = frm.doc.direction;

  const out_date = direction === "Export" ? row.pick_up_empty_date : row.gate_out_date;
  const return_date = direction === "Export" ? row.gate_in_full_date : row.gate_in_date;

  // D&D Calculation
  if (base_date && !isNaN(frm.doc.dnd_free_days)) {
    const last_free_day = frm.doc.dnd_free_days > 0
      ? frappe.datetime.add_days(base_date, frm.doc.dnd_free_days - 1)
      : frappe.datetime.add_days(base_date, -1);
    const dnd_start = frappe.datetime.add_days(last_free_day, 1);
    const dnd_end = row.to_be_returned ? return_date || today : out_date || today;

    if (frappe.datetime.obj_to_str(dnd_end) > frappe.datetime.obj_to_str(last_free_day)) {
      row.dnd_days_accumulated = frappe.datetime.get_diff(dnd_end, dnd_start) + 1;
    } else {
      row.dnd_days_accumulated = 0;
    }
  } else {
    row.dnd_days_accumulated = 0;
  }

  // Port Storage Calculation
  if (base_date && !isNaN(frm.doc.port_free_days)) {
    const last_free_day = frm.doc.port_free_days > 0
      ? frappe.datetime.add_days(base_date, frm.doc.port_free_days - 1)
      : frappe.datetime.add_days(base_date, -1);
    const storage_start = frappe.datetime.add_days(last_free_day, 1);
    const storage_end = out_date || today;

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

function update_total_dnd_days(frm) {
  let total = 0;
  (frm.doc.container_details || []).forEach(row => {
    total += parseInt(row.dnd_days_accumulated || 0);
  });
  (frm.doc.general_cargo_details || []).forEach(row => {
    total += parseInt(row.dnd_days_accumulated || 0);
  });
  if (frm.doc.total_dnd_days !== total) {
    frm.set_value('total_dnd_days', total);
  }
}

function update_total_storage_days(frm) {
  let total = 0;
  (frm.doc.container_details || []).forEach(row => {
    total += parseInt(row.storage_days_accumulated || 0);
  });
  (frm.doc.general_cargo_details || []).forEach(row => {
    total += parseInt(row.storage_days_accumulated || 0);
  });
  if (frm.doc.total_storage_days !== total) {
    frm.set_value('total_storage_days', total);
  }
}

// ========================================================
// CARGO COUNT SUMMARY FIELD (cargo_count)
// - Shows container breakdown or package count
// - Depends on cargo_type = "Containerised" or "General Cargo"
// ========================================================
function update_cargo_count(frm) {
  let cargo_type = frm.doc.cargo_type;
  let summary = "";

  if (cargo_type === "Containerised") {
    let container_summary = {};
    (frm.doc.container_details || []).forEach(row => {
      if (row.container_type) {
        container_summary[row.container_type] = (container_summary[row.container_type] || 0) + 1;
      }
    });

    let parts = [];
    for (let type in container_summary) {
      parts.push(`${container_summary[type]} x ${type}`);
    }

    summary = parts.join(", ");
  }

  if (cargo_type === "General Cargo") {
    const count = frm.doc.general_cargo_details?.length || 0;
    if (count > 0) {
      summary = `${count} x Packages`;
    }
  }

  if (frm.doc.cargo_count !== summary) {
    frm.set_value("cargo_count", summary);
  }
}

// --- Triggers ---
frappe.ui.form.on('Container Details', {
  container_type: update_cargo_count,
  container_details_remove: update_cargo_count,
  gate_out_full_date: update_container_days,
  pick_up_empty_date: update_container_days,
  gate_in_empty_date: update_container_days,
  gate_in_full_date: update_container_days,
  to_be_returned: update_container_days,
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

frappe.ui.form.on('General Cargo Details', {
  item_description: update_cargo_count,
  general_cargo_details_remove: update_cargo_count,
  gate_out_date: update_general_days,
  pick_up_empty_date: update_general_days,
  gate_in_date: update_general_days,
  gate_in_full_date: update_general_days,
  to_be_returned: update_general_days
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

