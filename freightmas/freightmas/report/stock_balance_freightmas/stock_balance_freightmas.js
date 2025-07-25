// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance FreightMas"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
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
            "on_change": function () {
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
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
            "get_query": function() {
                var company = frappe.query_report.get_filter_value('company');
                return {
                    "filters": {
                        "company": company
                    }
                }
            }
        },
        {
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return {
                    "filters": {
                        "disabled": 0
                    }
                }
            }
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "warehouse_type",
            "label": __("Warehouse Type"),
            "fieldtype": "Link",
            "options": "Warehouse Type"
        },
        {
            "fieldname": "include_zero_stock_items",
            "label": __("Include Zero Stock Items"),
            "fieldtype": "Check",
            "default": 0
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Color negative balance quantities in red, positive stays default color
        if (column.fieldname == "balance_qty" && data && data.balance_qty < 0) {
            value = "<span style='color:red'>" + value + "</span>";
        }
        
        // Color negative opening quantities in red
        if (column.fieldname == "opening_qty" && data && data.opening_qty < 0) {
            value = "<span style='color:red'>" + value + "</span>";
        }
        
        // Color positive in_qty values in green
        if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
            value = "<span style='color:green'>" + value + "</span>";
        }
        
        // Color positive out_qty values in blue
        if (column.fieldname == "out_qty" && data && data.out_qty > 0) {
            value = "<span style='color:blue'>" + value + "</span>";
        }
        
        // Positive opening quantities and zero values remain default color (no formatting needed)
        
        return value;
    },

    "onload": function(report) {
        // Set default company if available
        if (frappe.defaults.get_user_default("Company")) {
            report.set_filter_value("company", frappe.defaults.get_user_default("Company"));
        }

        // Add Export buttons
        report.page.add_inner_button('Export to Excel', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_excel?report_name=Stock Balance FreightMas&filters=${query}`;
            window.open(url);
        }, 'Export');

        report.page.add_inner_button('Export to PDF', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=Stock Balance FreightMas&filters=${query}`;
            window.open(url);
        }, 'Export');

        // Add a stand-alone "Clear Filters" button
        report.page.add_inner_button('Clear Filters', function() {
            // Clear all filters to defaults
            report.filters.forEach(filter => {
                let default_value = filter.df.default || "";
                if (filter.df.fieldname === 'from_date') {
                    default_value = frappe.datetime.month_start();
                } else if (filter.df.fieldname === 'to_date') {
                    default_value = frappe.datetime.month_end();
                } else if (filter.df.fieldname === 'company') {
                    default_value = frappe.defaults.get_user_default("Company") || "";
                } else if (filter.df.fieldname === 'date_range') {
                    default_value = "This Month";
                } else if (filter.df.fieldname === 'include_zero_stock_items') {
                    default_value = 0;
                }
                report.set_filter_value(filter.df.fieldname, default_value);
            });
            
            // Refresh the report after clearing filters
            setTimeout(function() {
                report.refresh();
            }, 500);
        });
    }
};
