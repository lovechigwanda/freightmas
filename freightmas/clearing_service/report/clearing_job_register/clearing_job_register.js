// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Clearing Job Register"] = {
    "filters": [
        {
            "fieldname": "date_from",
            "label": "Date Created From",
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0,
            "width": "120px"
        },
        {
            "fieldname": "date_to",
            "label": "Date Created To",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0,
            "width": "120px"
        },
        {
            "fieldname": "direction",
            "label": "Direction",
            "fieldtype": "Select",
            "options": "\nImport\nExport",
            "reqd": 0,
            "width": "100px"
        },
        {
            "fieldname": "status",
            "label": "Status",
            "fieldtype": "Select",
            "options": "\nDraft\nIn Progress\nCompleted\nCancelled",
            "reqd": 0,
            "width": "120px"
        }
    ],

    onload: function (report) {
        // Excel Export Button
        report.page.add_inner_button("Export to Excel", function () {
            const filters = report.get_filter_values(true);
            const params = new URLSearchParams(filters).toString();
            window.location.href = `/api/method/freightmas.api.download_clearing_job_register_excel?${params}`;
        });
    }
};

