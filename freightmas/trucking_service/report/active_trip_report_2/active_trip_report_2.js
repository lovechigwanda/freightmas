// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt


frappe.query_reports["Active Trip Report 2"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
            reqd: 0
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate(),
            reqd: 0
        },
        {
            fieldname: "client",
            label: __("Client"),
            fieldtype: "Link",
            options: "Customer",
            reqd: 0
        }
    ]
};
