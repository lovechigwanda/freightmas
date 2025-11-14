frappe.query_reports["Unbilled Forwarding Jobs"] = {
    filters: [
        {
            fieldname: "date_range",
            label: __("Date Range"),
            fieldtype: "Select",
            options: "\nToday\nYesterday\nThis Week\nLast Week\nThis Month\nLast Month\nThis Year\nLast Year\nCustom",
            default: "This Month",
            on_change: function() {
                if (window.FreightmasReportUtils && window.FreightmasReportUtils.apply_date_range_filter) {
                    window.FreightmasReportUtils.apply_date_range_filter();
                }
            }
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
            fieldname: "customer_reference",
            label: __("Reference"),
            fieldtype: "Data"
        },
        {
            fieldname: "direction",
            label: __("Direction"),
            fieldtype: "Select",
            options: "\nImport\nExport"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nSubmitted\nCompleted"
        }
    ],
    onload: function(report) {
        if (window.FreightmasReportUtils && window.FreightmasReportUtils.setup_standard_export_buttons) {
            window.FreightmasReportUtils.setup_standard_export_buttons(report, "Unbilled Forwarding Jobs");
        }
    }
};
