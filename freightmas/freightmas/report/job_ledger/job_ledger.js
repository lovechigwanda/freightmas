// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Job Ledger"] = {
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
      fieldname: "job_type",
      label: __("Job Type"),
      fieldtype: "Select",
      options: "Forwarding Job\nClearing Job\nBorder Clearing Job",
      default: "Forwarding Job",
      reqd: 1,
      on_change: function () {
        frappe.query_report.set_filter_value("job", "");
      },
    },
    {
      fieldname: "job",
      label: __("Job (leave empty for all jobs in period)"),
      fieldtype: "Dynamic Link",
      get_options: function () {
        let job_type = frappe.query_report.get_filter_value("job_type");
        if (!job_type) {
          frappe.throw(__("Please select Job Type first"));
        }
        return job_type;
      },
    },
    {
      fieldname: "date_basis",
      label: __("Date Based On"),
      fieldtype: "Select",
      options: "Date Created\nRevenue Recognised On",
      default: "Date Created",
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.month_start(),
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "consolidated",
      label: __("Consolidated (one row per voucher and account)"),
      fieldtype: "Check",
      default: 0,
    },
    {
      fieldname: "show_cancelled",
      label: __("Show Cancelled Entries"),
      fieldtype: "Check",
      default: 0,
    },
  ],

  onload: function (report) {
    report.page.add_inner_button(
      __("Export Excel"),
      function () {
        let filters = report.get_values();
        open_url_post(
          "/api/method/freightmas.freightmas.report.job_ledger.job_ledger.export_excel",
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
          "/api/method/freightmas.freightmas.report.job_ledger.job_ledger.export_pdf",
          { filters: JSON.stringify(filters) }
        );
      },
      __("Export")
    );
  },
};
