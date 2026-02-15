// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Accounts Receivable Payable Statement"] = {
    onload: function(report) {
        report.page.add_inner_button('Export to Excel', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_ar_ap_statement_to_excel?filters=${query}`;
            window.open(url);
        }, 'Export');

        report.page.add_inner_button('Export to PDF', function() {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_ar_ap_statement_to_pdf?filters=${query}`;
            window.open(url);
        }, 'Export');

        report.page.add_inner_button('Clear Filters', function() {
            report.filters.forEach(filter => {
                let default_value = filter.df.default || "";
                report.set_filter_value(filter.df.fieldname, default_value);
            });
            report.refresh();
        });
    },

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
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Select",
            "options": ["Customer", "Supplier"],
            "default": "Customer",
            "reqd": 1,
            "on_change": function() {
                let party_type = frappe.query_report.get_filter_value('party_type');
                frappe.query_report.toggle_filter_display('party', true);
                frappe.query_report.set_filter_value('party', '');

                let party_field = frappe.query_report.get_filter('party');
                party_field.df.options = party_type;
                party_field.df.label = __(party_type);
                party_field.refresh();
            }
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "Link",
            "options": "Customer",
            "reqd": 1,
            "get_query": function() {
                let party_type = frappe.query_report.get_filter_value('party_type');
                if (!party_type) {
                    frappe.throw(__("Please select Party Type first"));
                }
                return {
                    filters: {
                        'disabled': 0
                    }
                };
            }
        },
        {
            "fieldname": "show_fully_paid",
            "label": __("Include Fully Paid Invoices"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "include_draft_invoices",
            "label": __("Include Draft Invoices"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "include_cancelled",
            "label": __("Include Cancelled Documents"),
            "fieldtype": "Check",
            "default": 0
        }
    ]
};
