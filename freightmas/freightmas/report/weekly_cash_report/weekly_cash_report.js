// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Weekly Cash Report"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      reqd: 1,
    },
    {
      fieldname: "week_ending_date",
      label: __("Week Ending Date (Saturday)"),
      fieldtype: "Date",
      default: _get_last_saturday(),
      reqd: 1,
      description: __("Must be a Saturday — the report covers the preceding Sunday through this date."),
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (!data) return value;

    var rt = data.row_type;

    // Section headers: bold white text on blue background
    if (rt === "section_header") {
      value =
        '<b style="color:#fff; background:#305496; padding:2px 6px; display:block;">' +
        (value || "&nbsp;") +
        "</b>";
    }

    // Opening and closing balance rows: bold
    if (rt === "opening" || rt === "closing") {
      value = "<b>" + (value || "") + "</b>";
    }

    // Total rows: bold with light grey background
    if (rt === "total") {
      value =
        '<b style="background:#f2f2f2; padding:1px 4px; display:block;">' +
        (value || "") +
        "</b>";
    }

    // Statement balance: italic
    if (rt === "statement") {
      value = "<i>" + (value || "") + "</i>";
    }

    // Difference: red if non-zero numeric value
    if (rt === "difference" && column.fieldtype === "Currency") {
      var raw = data[column.fieldname];
      if (raw !== null && raw !== undefined && raw !== 0) {
        value = '<span style="color:#e74c3c;">' + value + "</span>";
      }
    }

    // Spacer rows: thin divider line on description column
    if (rt === "spacer" && column.fieldname === "description") {
      value = '<hr style="margin:1px 0; border:none; border-top:1px solid #ddd;">';
    }

    // Negative values in red (for all currency columns)
    if (
      column.fieldtype === "Currency" &&
      data[column.fieldname] !== null &&
      data[column.fieldname] !== undefined &&
      data[column.fieldname] < 0 &&
      rt !== "difference"
    ) {
      value = '<span style="color:#e74c3c;">' + value + "</span>";
    }

    return value;
  },

  onload: function (report) {
    // Export to Excel
    report.page.add_inner_button(
      __("Export Excel"),
      function () {
        var filters = report.get_values();
        open_url_post(
          "/api/method/freightmas.freightmas.report.weekly_cash_report.weekly_cash_report.export_excel",
          { filters: JSON.stringify(filters) }
        );
      },
      __("Export")
    );

    // Open statement balances form for this week
    report.page.add_inner_button(
      __("Enter Statement Balances"),
      function () {
        var filters = report.get_values();
        if (!filters.company || !filters.week_ending_date) {
          frappe.msgprint(__("Please set Company and Week Ending Date first."));
          return;
        }
        frappe.set_route("List", "Weekly Cash Statement Balance", {
          company: filters.company,
          week_ending_date: filters.week_ending_date,
        });
      },
      __("Actions")
    );
  },
};

function _get_last_saturday() {
  var today = frappe.datetime.get_today();
  var dow = new Date(today).getDay(); // 0=Sunday, 6=Saturday
  var daysBack = dow === 6 ? 0 : dow + 1; // days back to reach Saturday
  return frappe.datetime.add_days(today, -daysBack);
}
