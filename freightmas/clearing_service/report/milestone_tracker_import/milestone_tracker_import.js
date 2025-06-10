// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Milestone Tracker Import"] = {
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
            on_change: function() {
                let date_range = frappe.query_report.get_filter_value('date_range');
                let today = frappe.datetime.get_today();
                let from_date, to_date;

                switch(date_range) {
                    case "Today":
                        from_date = to_date = today;
                        break;
                    case "Yesterday":
                        from_date = to_date = frappe.datetime.add_days(today, -1);
                        break;
                    case "This Week":
                        from_date = frappe.datetime.week_start();
                        to_date = frappe.datetime.week_end();
                        break;
                    case "Last Week":
                        from_date = frappe.datetime.add_days(frappe.datetime.week_start(), -7);
                        to_date = frappe.datetime.add_days(frappe.datetime.week_end(), -7);
                        break;
                    case "This Month":
                        from_date = frappe.datetime.month_start();
                        to_date = frappe.datetime.month_end();
                        break;
                    case "Last Month":
                        from_date = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
                        to_date = frappe.datetime.add_days(frappe.datetime.month_start(), -1);
                        break;
                    case "This Year":
                        from_date = frappe.datetime.year_start();
                        to_date = frappe.datetime.year_end();
                        break;
                    case "Last Year":
                        let today_parts = today.split('-');
                        let last_year = parseInt(today_parts[0], 10) - 1;
                        from_date = `${last_year}-01-01`;
                        to_date = `${last_year}-12-31`;
                        break;
                    default:
                        from_date = frappe.query_report.get_filter_value('from_date');
                        to_date = frappe.query_report.get_filter_value('to_date');
                }

                if (date_range && date_range !== "Custom" && date_range !== "") {
                    frappe.query_report.set_filter_value('from_date', from_date);
                    frappe.query_report.set_filter_value('to_date', to_date);
                }
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
            window.location.href = `/api/method/freightmas.api.download_milestone_tracker_import_excel?filters=${query}`;
        });
    }
};
