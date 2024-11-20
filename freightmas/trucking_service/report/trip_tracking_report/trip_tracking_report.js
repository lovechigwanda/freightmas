// Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

// trip_tracking_report.js

frappe.query_reports["Trip Tracking Report"] = {
    filters: [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.nowdate(),
            "reqd": 1
        }
    ]
};
