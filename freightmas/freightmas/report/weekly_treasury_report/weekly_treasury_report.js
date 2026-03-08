// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Weekly Treasury Report"] = {
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
      label: __("Week Ending Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "comparison_period",
      label: __("Comparison Period"),
      fieldtype: "Select",
      options: "\nPrevious Week\nSame Week Last Month",
      default: "",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (!data) return value;

    // Section headers — bold blue
    if (data.row_type === "header") {
      if (column.fieldname === "section" || column.fieldname === "label") {
        value =
          '<b style="font-size:13px; color:#305496;">' + value + "</b>";
      }
    }

    // Subtotals — bold with light background
    if (data.row_type === "subtotal") {
      value = "<b>" + value + "</b>";
    }

    // Spacer rows — render as thin horizontal line
    if (data.row_type === "spacer" && column.fieldname === "section") {
      value = '<hr style="margin:2px 0; border-top:1px solid #ddd;">';
    }

    // Negative amounts in red
    if (
      column.fieldtype === "Currency" &&
      data[column.fieldname] &&
      data[column.fieldname] < 0
    ) {
      value = '<span style="color:#e74c3c;">' + value + "</span>";
    }

    return value;
  },

  onload: function (report) {
    report.page.add_inner_button(
      __("Export Excel"),
      function () {
        let filters = report.get_values();
        open_url_post(
          "/api/method/freightmas.freightmas.report.weekly_treasury_report.weekly_treasury_report.export_excel",
          { filters: JSON.stringify(filters) }
        );
      },
      __("Export")
    );

    report.page.add_inner_button(
      __("Export PDF"),
      function () {
        let filters = report.get_values();
        open_url_post(
          "/api/method/freightmas.freightmas.report.weekly_treasury_report.weekly_treasury_report.export_pdf",
          { filters: JSON.stringify(filters) }
        );
      },
      __("Export")
    );
  },
};
