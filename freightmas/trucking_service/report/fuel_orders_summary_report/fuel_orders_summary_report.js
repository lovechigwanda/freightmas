// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt


frappe.query_reports["Fuel Orders Summary Report"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: ["", "Draft", "Pending Approval", "Rejected", "Approved", "Completed"],
            default: ""
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier"
        }
    ]
};



