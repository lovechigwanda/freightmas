/* FreightMas Report Common JavaScript Utilities
 * Common utilities and patterns for FreightMas reports to ensure consistency.
 */

// Standard date range filter configuration
function get_standard_date_range_filter(default_range = "This Month") {
    return {
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
        default: default_range,
        on_change: function() {
            apply_date_range_filter();
        }
    };
}

// Apply date range selection to from_date and to_date filters
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
            // For "Custom" option, don't auto-populate
            return;
    }

    if (date_range && date_range !== "Custom" && date_range !== "") {
        frappe.query_report.set_filter_value('from_date', from_date);
        frappe.query_report.set_filter_value('to_date', to_date);
    }
}

// Standard filter configurations
const STANDARD_FILTERS = {
    date_range: function(default_range = "This Month") {
        return get_standard_date_range_filter(default_range);
    },
    
    from_date: function(default_months_back = -1) {
        return {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), default_months_back),
            reqd: 0
        };
    },
    
    to_date: function() {
        return {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 0
        };
    },
    
    customer: function(required = false) {
        return {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            reqd: required ? 1 : 0,
            only_select: true
        };
    },
    
    company: function(required = false) {
        return {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: required ? 1 : 0
        };
    },
    
    status: function(options = ["", "Draft", "In Progress", "Completed", "Cancelled"]) {
        return {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: options.join("\n")
        };
    },
    
    direction: function() {
        return {
            fieldname: "direction",
            label: __("Direction"),
            fieldtype: "Select",
            options: ["", "Import", "Export"]
        };
    },
    
    customer_reference: function() {
        return {
            fieldname: "customer_reference",
            label: __("Reference"),
            fieldtype: "Data"
        };
    },
    
    bl_number: function() {
        return {
            fieldname: "bl_number",
            label: __("BL Number"),
            fieldtype: "Data"
        };
    },
    
    container_no: function() {
        return {
            fieldname: "container_no",
            label: __("Container No"),
            fieldtype: "Data"
        };
    }
};

// Standard export button setup
function setup_standard_export_buttons(report, report_name, custom_exports = {}) {
    // Excel Export
    report.page.add_inner_button(__('Export to Excel'), function() {
        const filters = report.get_filter_values(true);
        const query = encodeURIComponent(JSON.stringify(filters));
        
        let url;
        if (custom_exports.excel) {
            url = `/api/method/${custom_exports.excel}?report_name=${encodeURIComponent(report_name)}&filters=${query}`;
        } else {
            url = `/api/method/freightmas.api.export_report_to_excel?report_name=${encodeURIComponent(report_name)}&filters=${query}`;
        }
        window.open(url);
    }, __('Export'));

    // PDF Export  
    report.page.add_inner_button(__('Export to PDF'), function() {
        const filters = report.get_filter_values(true);
        const query = encodeURIComponent(JSON.stringify(filters));
        
        let url;
        if (custom_exports.pdf) {
            url = `/api/method/${custom_exports.pdf}?report_name=${encodeURIComponent(report_name)}&filters=${query}`;
        } else {
            url = `/api/method/freightmas.api.export_report_to_pdf?report_name=${encodeURIComponent(report_name)}&filters=${query}`;
        }
        window.open(url);
    }, __('Export'));

    // Clear Filters - Standalone button between Export and Actions
    report.page.add_button(__('Clear Filters'), function() {
        clear_all_filters(report);
    });
}

// Clear all filters to defaults
function clear_all_filters(report) {
    report.filters.forEach(filter => {
        let default_value = filter.df.default || "";
        if (filter.df.fieldtype === "Select" && filter.df.options) {
            // For Select fields, use first option as default if no explicit default
            if (!default_value) {
                const options = filter.df.options.split('\n').filter(opt => opt.trim());
                default_value = options.length > 0 ? options[0] : "";
            }
        }
        report.set_filter_value(filter.df.fieldname, default_value);
    });
    
    // Refresh the report
    report.refresh();
}

// Validate filter values
function validate_filters(filters) {
    // Date validation
    if (filters.from_date && filters.to_date) {
        const from_date = new Date(filters.from_date);
        const to_date = new Date(filters.to_date);
        
        if (from_date > to_date) {
            frappe.msgprint(__("From Date cannot be greater than To Date"));
            return false;
        }
    }
    
    return true;
}

// Create standard filter array for common report patterns
function get_job_register_filters() {
    return [
        STANDARD_FILTERS.date_range(),
        STANDARD_FILTERS.from_date(),
        STANDARD_FILTERS.to_date(),
        STANDARD_FILTERS.customer(),
        STANDARD_FILTERS.customer_reference(),
        STANDARD_FILTERS.status()
    ];
}

function get_tracking_filters() {
    return [
        STANDARD_FILTERS.date_range(),
        STANDARD_FILTERS.from_date(),
        STANDARD_FILTERS.to_date(),
        STANDARD_FILTERS.customer(),
        STANDARD_FILTERS.customer_reference(),
        STANDARD_FILTERS.direction(),
        STANDARD_FILTERS.bl_number(),
        STANDARD_FILTERS.status()
    ];
}

function get_container_tracker_filters() {
    return [
        STANDARD_FILTERS.date_range(),
        STANDARD_FILTERS.from_date(),
        STANDARD_FILTERS.to_date(),
        STANDARD_FILTERS.customer(),
        STANDARD_FILTERS.customer_reference(),
        STANDARD_FILTERS.direction(),
        STANDARD_FILTERS.bl_number(),
        STANDARD_FILTERS.container_no(),
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nIn Port\nNot Returned\nReturned\nDelivered"
        }
    ];
}

// Report configuration factory
function create_standard_report_config(report_name, filter_type = "job_register", custom_config = {}) {
    let filters;
    
    switch (filter_type) {
        case "job_register":
            filters = get_job_register_filters();
            break;
        case "tracking":
            filters = get_tracking_filters();
            break;
        case "container_tracker":
            filters = get_container_tracker_filters();
            break;
        default:
            filters = [];
    }
    
    // Merge custom filters
    if (custom_config.additional_filters) {
        filters = filters.concat(custom_config.additional_filters);
    }
    
    const config = {
        filters: filters,
        
        onload: function(report) {
            setup_standard_export_buttons(report, report_name, custom_config.exports || {});
            
            // Custom onload logic
            if (custom_config.onload) {
                custom_config.onload(report);
            }
        }
    };
    
    // Merge any other custom configuration
    Object.keys(custom_config).forEach(key => {
        if (key !== "additional_filters" && key !== "exports" && key !== "onload") {
            config[key] = custom_config[key];
        }
    });
    
    return config;
}

// Make utilities available globally
window.FreightmasReportUtils = {
    STANDARD_FILTERS,
    setup_standard_export_buttons,
    clear_all_filters,
    validate_filters,
    get_job_register_filters,
    get_tracking_filters,
    get_container_tracker_filters,
    create_standard_report_config,
    apply_date_range_filter
};