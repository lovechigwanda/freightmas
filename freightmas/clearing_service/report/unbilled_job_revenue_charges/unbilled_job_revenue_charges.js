// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Unbilled Job Revenue Charges"] = {
  filters: [
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      default: frappe.datetime.month_start(),
      reqd: 0,
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      default: frappe.datetime.month_end(),
      reqd: 0,
    },
    {
      fieldname: "job_no",
      label: "Job No",
      fieldtype: "Link",
      options: "Clearing Job",
      only_select: true, 
      get_query: () => {
        return {
          query: "freightmas.clearing_service.report.unbilled_job_revenue_charges.unbilled_job_revenue_charges.get_job_nos_with_uninvoiced_charges"
        };
      }
    },
    {
      fieldname: "currency",
      label: "Currency",
      fieldtype: "Link",
      options: "Currency",
      only_select: true, 
      get_query: () => {
        return {
          query: "freightmas.clearing_service.report.unbilled_job_revenue_charges.unbilled_job_revenue_charges.get_currencies_with_uninvoiced_charges"
        };
      }
    }
  ]
};