// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors  
// For license information, please see license.txt

frappe.query_reports["FM Accounts Payable Outstanding"] = {
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
            "fieldname": "report_date",
            "label": __("Report Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "supplier_group",
            "label": __("Supplier Group"),
            "fieldtype": "Link", 
            "options": "Supplier Group"
        },
        {
            "fieldname": "include_proforma_invoices",
            "label": __("Include Proforma Invoices"),
            "fieldtype": "Check",
            "default": 0
        }
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname == "outstanding_amount" && data && data.outstanding_amount > 0) {
            value = `<span style='color:red!important; font-weight:bold'>${value}</span>`;
        }
        
        return value;
    },

    "onload": function(report) {
        // Add Export buttons
        report.page.add_inner_button('Export to Excel', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_excel?report_name=FM Accounts Payable Outstanding&filters=${query}`;
            window.open(url);
        }, 'Export');

        report.page.add_inner_button('Export to PDF', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=FM Accounts Payable Outstanding&filters=${query}`;
            window.open(url);
        }, 'Export');

        // Add Clear Filters button
        report.page.add_inner_button('Clear Filters', function() {
            report.filters.forEach(filter => {
                let default_value = filter.df.default || "";
                if (filter.df.fieldtype === "Check") {
                    default_value = filter.df.default || 0;
                }
                report.set_filter_value(filter.df.fieldname, default_value);
            });
            report.refresh();
        });
        
        // Add refresh button
        report.page.add_inner_button('Refresh Data', function() {
            report.refresh();
        });
    },

    "initial_depth": 0
};
