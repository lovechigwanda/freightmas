frappe.query_reports["Container Tracker Imports"] = {
    filters: [
        {
            fieldname: "date_range",
            label: __("Date Range"),
            fieldtype: "Select",
            options: [
                "",
                "Today",
                "Yesterday",
                "This Week",
                "Last Week",
                "This Month",
                "Last Month",
                "This Year",
                "Last Year",
                "Custom"
            ],
            default: "This Month",
            on_change: function () {
                // ...existing code...
            }
        },
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
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            get_query: function() {
                return {
                    filters: {
                        disabled: 0
                    }
                };
            }
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [
                "",
                "Active",
                "Inactive",
                "Pending",
                "Completed"
            ],
            default: "Active"
        }
    ]
};