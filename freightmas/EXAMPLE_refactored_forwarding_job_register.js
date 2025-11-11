// Example: Refactored Forwarding Job Register JavaScript
// This shows how to use the new report utilities for consistent JavaScript

// Include the common utilities
frappe.require('/assets/freightmas/js/report_commons.js');

frappe.query_reports["Forwarding Job Register"] = 
    FreightmasReportUtils.create_standard_report_config(
        "Forwarding Job Register",
        "job_register", // Use standard job register filters
        {
            // Any additional custom configuration
            additional_filters: [
                // Add any report-specific filters here
            ],
            
            // Custom export endpoints if needed
            exports: {
                // excel: "custom.export.method", // Optional custom export
                // pdf: "custom.pdf.export"       // Optional custom export
            },
            
            // Custom onload logic if needed
            onload: function(report) {
                // Any additional custom setup can go here
                console.log("Forwarding Job Register loaded");
            }
        }
    );

// Alternative manual approach if more customization is needed:
/*
frappe.query_reports["Forwarding Job Register"] = {
    filters: FreightmasReportUtils.get_job_register_filters(),
    
    onload: function(report) {
        FreightmasReportUtils.setup_standard_export_buttons(report, "Forwarding Job Register");
        
        // Additional custom logic
    }
};
*/