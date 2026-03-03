// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Expenses Detail Report"] = {
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
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.year_start(),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "fiscal_year",
      label: __("Fiscal Year"),
      fieldtype: "Link",
      options: "Fiscal Year",
      on_change: function () {
        let fiscal_year = frappe.query_report.get_filter_value("fiscal_year");
        if (fiscal_year) {
          frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
            let fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
            frappe.query_report.set_filter_value({
              from_date: fy.year_start_date,
              to_date: fy.year_end_date,
            });
          });
        }
      },
    },
    {
      fieldname: "cost_center",
      label: __("Cost Center"),
      fieldtype: "Link",
      options: "Cost Center",
      get_query: function () {
        let company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            company: company,
          },
        };
      },
    },
    {
      fieldname: "account",
      label: __("Expense Account"),
      fieldtype: "Link",
      options: "Account",
      get_query: function () {
        let company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            root_type: "Expense",
            company: company,
            is_group: 0,
          },
        };
      },
    },
    {
      fieldname: "party_type",
      label: __("Party Type"),
      fieldtype: "Select",
      options: "\nCustomer\nSupplier",
    },
    {
      fieldname: "party",
      label: __("Party"),
      fieldtype: "Dynamic Link",
      options: "party_type",
      get_query: function () {
        let party_type = frappe.query_report.get_filter_value("party_type");
        if (!party_type) {
          frappe.throw(__("Please select Party Type first"));
        }
        return {
          doctype: party_type,
        };
      },
    },
    {
      fieldname: "voucher_type",
      label: __("Voucher Type"),
      fieldtype: "Select",
      options:
        "\nSales Invoice\nPurchase Invoice\nJournal Entry\nPayment Entry\nStock Entry",
    },
    {
      fieldname: "group_by",
      label: __("Group By"),
      fieldtype: "Select",
      options:
        "Group by Account\nGroup by Cost Center\nGroup by Party\nGroup by Voucher Type\nUngrouped",
      default: "Group by Account",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (data && data.is_group_total) {
      value = "<b>" + value + "</b>";
    }
    return value;
  },
};
