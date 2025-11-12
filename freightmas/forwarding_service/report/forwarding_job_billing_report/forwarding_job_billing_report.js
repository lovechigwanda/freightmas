// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Forwarding Job Billing Report"] = {
    "filters": [
        {
            "fieldname": "date_range",
            "label": __("Date Range"),
            "fieldtype": "Select",
            "options": [
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
            "default": "This Month",
            "on_change": function() {
                apply_date_range_filter();
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date", 
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        },
        {
            "fieldname": "customer_reference",
            "label": __("Reference"),
            "fieldtype": "Data"
        }
    ],
    "onload": function(report) {
        setup_standard_export_buttons(report, "Forwarding Job Billing Report");
    }
};

function apply_date_range_filter() {
    let date_range = frappe.query_report.get_filter_value('date_range');
    let today = frappe.datetime.get_today();
    let from_date, to_date;
    switch (date_range) {
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
            const lastYear = (new Date()).getFullYear() - 1;
            from_date = `${lastYear}-01-01`;
            to_date = `${lastYear}-12-31`;
            break;
        default:
            return;
    }
    if (date_range && date_range !== "Custom" && date_range !== "") {
        frappe.query_report.set_filter_value('from_date', from_date);
        frappe.query_report.set_filter_value('to_date', to_date);
    }
}

function setup_standard_export_buttons(report, report_name) {
    report.page.add_inner_button(__('Export to Excel'), function() {
        const filters = report.get_filter_values(true);
        const query = encodeURIComponent(JSON.stringify(filters));
        const url = `/api/method/freightmas.api.export_report_to_excel?report_name=${encodeURIComponent(report_name)}&filters=${query}`;
        window.open(url);
    }, __('Export'));
    report.page.add_inner_button(__('Export to PDF'), function() {
        const filters = report.get_filter_values(true);
        const query = encodeURIComponent(JSON.stringify(filters));
        const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=${encodeURIComponent(report_name)}&filters=${query}`;
        window.open(url);
    }, __('Export'));
    report.page.add_button(__('Clear Filters'), function() {
        report.set_filter_value('date_range', 'This Month');
        report.set_filter_value('from_date', frappe.datetime.add_months(frappe.datetime.get_today(), -1));
        report.set_filter_value('to_date', frappe.datetime.get_today());
        report.set_filter_value('customer', '');
        report.set_filter_value('customer_reference', '');
        report.refresh();
    });
}
