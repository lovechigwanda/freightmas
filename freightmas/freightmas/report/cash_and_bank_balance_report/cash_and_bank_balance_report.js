// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Cash and Bank Balance Report"] = {
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
      fieldname: "as_of_date",
      label: __("As of Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "account",
      label: __("Account"),
      fieldtype: "Link",
      options: "Account",
      get_query: function () {
        let company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            root_type: "Asset",
            account_type: ["in", ["Cash", "Bank"]],
            company: company,
            is_group: 0,
          },
        };
      },
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (data && data.is_total_row) {
      value = "<b>" + value + "</b>";
    }
    return value;
  },

  onload: function (report) {
    report.page.add_inner_button(
      __("Export Excel"),
      function () {
        let filters = report.get_values();
        open_url_post(
          "/api/method/freightmas.freightmas.report.cash_and_bank_balance_report.cash_and_bank_balance_report.export_excel",
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
          "/api/method/freightmas.freightmas.report.cash_and_bank_balance_report.cash_and_bank_balance_report.export_pdf",
          { filters: JSON.stringify(filters) }
        );
      },
      __("Export")
    );
  },
};
