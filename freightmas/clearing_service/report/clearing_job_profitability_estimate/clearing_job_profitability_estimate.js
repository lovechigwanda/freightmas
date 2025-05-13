// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt



frappe.query_reports["Clearing Job Profitability Estimate"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "bl_number",
            label: __("BL Number"),
            fieldtype: "Data"
        },
        {
            fieldname: "direction",
            label: __("Direction"),
            fieldtype: "Select",
            options: ["", "Import", "Export"]
        }
    ]
}

