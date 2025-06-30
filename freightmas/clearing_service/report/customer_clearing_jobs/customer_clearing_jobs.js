// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Clearing Jobs"] = {
    filters: [
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            reqd: 1
        },
        {
            fieldname: "direction",
            label: __("Direction"),
            fieldtype: "Select",
            options: "\nImport\nExport"
        },
        {
            fieldname: "bl_number",
            label: __("BL Number"),
            fieldtype: "Data"
        }
    ],

    onload: function(report) {
        report.page.add_inner_button(__('Export PDF'), function() {
            let filters = report.get_values();
            if (!filters.customer) {
                frappe.msgprint(__('Please select a Customer to export the PDF.'));
                return;
            }
            let params = $.param({
                customer: filters.customer,
                direction: filters.direction || "",
                bl_number: filters.bl_number || ""
            });
            window.open(
                '/api/method/freightmas.clearing_service.report.customer_clearing_jobs.customer_clearing_jobs.export_customer_clearing_jobs_pdf?' + params,
                '_blank'
            );
        }, __("Tools"));
    }
};