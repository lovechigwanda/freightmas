// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Container Status Tracker"] = {
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
            label: "Client",
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
        },
        {
            fieldname: "bl_number",
            label: "BL No.",
            fieldtype: "Data"
        },
        {
            fieldname: "report_type",
            label: "Report Type",
            fieldtype: "Select",
            options: [
                "All",
                "Not Yet Loaded Out",
                "Loaded Not Returned",
                "With Storage",
                "With Demurrage",
                "Returned",
                "Returned No Charges",
                "Returned With Charges"
            ],
            default: "All",
            reqd: 1
        }
    ],

    onload: function (report) {
        // Excel Export Button
        report.page.add_inner_button("Export to Excel", function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            window.location.href = `/api/method/freightmas.api.download_container_status_excel?filters=${query}`;
        });

        // PDF Export Button
        report.page.add_inner_button("Export to PDF", function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            window.location.href = `/api/method/freightmas.api.download_container_status_pdf?filters=${query}`;
        });
    }
};
