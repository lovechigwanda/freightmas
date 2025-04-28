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

frappe.ui.form.on('Clearing Job', {
    refresh(frm) {
        calculate_clearing_totals(frm);
    },
    validate(frm) {
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

    frm.set_value('total_estimated_revenue', total_revenue);
    frm.set_value('total_estimated_cost', total_cost);
    frm.set_value('total_estimated_profit', total_revenue - total_cost);
}

///////////////////////////////////////////////////////////////////////////////////

