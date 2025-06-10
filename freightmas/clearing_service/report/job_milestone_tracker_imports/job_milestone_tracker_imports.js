// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Job Milestone Tracker Imports"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer",
            only_select: true
        },
        {
            fieldname: "job_no",
            label: "Job No",
            fieldtype: "Link",
            options: "Clearing Job",
            only_select: true
        }
    ],

    onload: function (report) {
        report.page.add_inner_button("Export to Excel", function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));

            // Trigger binary download directly via browser
            window.location.href = `/api/method/freightmas.api.download_job_milestone_excel?filters=${query}`;
        });
    }
};
