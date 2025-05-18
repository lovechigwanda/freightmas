// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt


frappe.query_reports["Job Lifecycle Tracker Imports"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 0
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 0
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer",
            only_select: true,
            reqd: 0
        },
        {
            fieldname: "job_no",
            label: "Job No",
            fieldtype: "Link",
            options: "Clearing Job",
            only_select: true,
            reqd: 0
        }
    ]
};
