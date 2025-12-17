// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors  
// For license information, please see license.txt

frappe.query_reports["FM Accounts Payable Summary"] = {
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
            "fieldname": "ageing_based_on",
            "label": __("Ageing Based On"),
            "fieldtype": "Select",
            "options": "Posting Date\nDue Date",
            "default": "Due Date"
        },
        {
            "fieldname": "range",
            "label": __("Ageing Range"),
            "fieldtype": "Data",
            "default": "30, 60, 90, 120"
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
            value = `<span style='color:red!important'>${value}</span>`;
        }
        
        // Highlight proforma amounts in blue
        if (column.fieldname == "proforma_amount" && data && data.proforma_amount > 0) {
            value = `<span style='color:blue!important; font-style:italic'>${value}</span>`;
        }
        
        return value;
    },

    "onload": function(report) {
        // Add Export buttons
        report.page.add_inner_button('Export to Excel', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_excel?report_name=FM Accounts Payable Summary&filters=${query}`;
            window.open(url);
        }, 'Export');

        report.page.add_inner_button('Export to PDF', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_pdf?report_name=FM Accounts Payable Summary&filters=${query}`;
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

        // Show/hide proforma column based on checkbox
        report.filter_inputs.include_proforma_invoices.on('change', function() {
            // Refresh to show/hide the proforma column
            setTimeout(() => {
                report.refresh();
            }, 100);
        });
    },

    "initial_depth": 0
};
