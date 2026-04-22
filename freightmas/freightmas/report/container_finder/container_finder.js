// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

const finderUtils = window.FreightmasReportUtils;

function get_container_finder_filters() {
    if (finderUtils && finderUtils.STANDARD_FILTERS) {
        return [
            finderUtils.STANDARD_FILTERS.date_range("This Month"),
            finderUtils.STANDARD_FILTERS.from_date(0),
            finderUtils.STANDARD_FILTERS.to_date(),
            finderUtils.STANDARD_FILTERS.customer(),
            finderUtils.STANDARD_FILTERS.bl_number(),
            finderUtils.STANDARD_FILTERS.container_no(),
            {
                fieldname: "include_cancelled",
                label: __("Include Cancelled"),
                fieldtype: "Check",
                default: 0,
            },
        ];
    }

    return [
        {
            fieldname: "date_range",
            label: __("Date Range"),
            fieldtype: "Select",
            options: ["", "Today", "Yesterday", "This Week", "Last Week", "This Month", "Last Month", "This Year", "Last Year", "Custom"],
            default: "This Month",
            on_change: function () {
                // Keep behavior consistent even when common utility script is unavailable.
                if (window.FreightmasReportUtils && window.FreightmasReportUtils.apply_date_range_filter) {
                    window.FreightmasReportUtils.apply_date_range_filter();
                }
            },
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "bl_number",
            label: __("BL Number"),
            fieldtype: "Data",
        },
        {
            fieldname: "container_no",
            label: __("Container No"),
            fieldtype: "Data",
        },
        {
            fieldname: "include_cancelled",
            label: __("Include Cancelled"),
            fieldtype: "Check",
            default: 0,
        },
    ];
}

frappe.query_reports["Container Finder"] = {
    filters: get_container_finder_filters(),

    onload: function (report) {
        if (finderUtils && finderUtils.setup_standard_export_buttons) {
            finderUtils.setup_standard_export_buttons(report, "Container Finder");
            return;
        }

        report.page.add_inner_button(__("Export to Excel"), function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_excel?report_name=${encodeURIComponent("Container Finder")}&filters=${query}`;
            window.open(url);
        }, __("Export"));

        report.page.add_inner_button(__("Export to PDF"), function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=${encodeURIComponent("Container Finder")}&filters=${query}`;
            window.open(url);
        }, __("Export"));
    },
};
