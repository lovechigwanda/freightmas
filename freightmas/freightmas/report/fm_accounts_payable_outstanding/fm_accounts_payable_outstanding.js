// Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
// For license information, please see license.txt

frappe.query_reports["FM Accounts Payable Outstanding"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier"
        },
        {
            fieldname: "include_draft_invoices",
            label: __("Include Draft Invoices"),
            fieldtype: "Check",
            default: 0
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        // Highlight total outstanding
        if (column.fieldname === "total_outstanding" && data.total_outstanding > 0) {
            value = `<span style="color:#c0392b; font-weight:600">${value}</span>`;
        }

        return value;
    },

    onload: function (report) {

        report.page.add_inner_button(__('Export to Excel'), function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_excel`
                + `?report_name=FM Accounts Payable Outstanding`
                + `&filters=${query}`;
            window.open(url);
        }, __('Export'));

        report.page.add_inner_button(__('Export to PDF'), function () {
            const filters = report.get_filter_values(true);
            const query = encodeURIComponent(JSON.stringify(filters));
            const url = `/api/method/freightmas.api.export_report_to_pdf`
                + `?report_name=FM Accounts Payable Outstanding`
                + `&filters=${query}`;
            window.open(url);
        }, __('Export'));

        report.page.add_inner_button(__('Clear Filters'), function () {
            report.filters.forEach(filter => {
                let default_value = filter.df.default || "";
                if (filter.df.fieldtype === "Check") {
                    default_value = filter.df.default || 0;
                }
                report.set_filter_value(filter.df.fieldname, default_value);
            });
            report.refresh();
        });

        report.page.add_inner_button(__('Refresh Data'), function () {
            report.refresh();
        });
    },

    initial_depth: 0
};
