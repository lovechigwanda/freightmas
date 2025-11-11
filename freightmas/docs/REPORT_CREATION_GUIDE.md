# FreightMas Report Creation Guide

This guide provides a standard template for creating new reports using the FreightMas report utilities framework.

## 📋 Standard Report Creation Prompt Template

Use this template when requesting a new report to ensure consistency with the established framework:

```
Create a new report for [SERVICE_NAME] called "[REPORT_NAME]" with the following requirements:

**Report Details:**
- Report Name: [REPORT_NAME] (e.g., "Trucking Job Profitability Report")
- Service Module: [SERVICE_MODULE] (e.g., trucking_service, clearing_service, forwarding_service)
- DocType: [DOCTYPE_NAME] (e.g., "Trucking Job", "Clearing Job")
- Report Type: Query Report

**Required Columns:**
- Standard columns: [LIST_STANDARD_COLUMNS] (e.g., job_id, job_date, customer, reference, status)
- Custom columns: [LIST_CUSTOM_COLUMNS] (e.g., truck_number, driver_name, route)

**Filters Required:**
- Date range (date_range) - Standard quick selection dropdown
- Date range (from_date, to_date) - Manual date selection
- Customer filter - Standard customer selection
- Customer Reference filter - Search by reference text
- [ADDITIONAL_FILTERS] (e.g., status, direction, company)

**Data Processing:**
- Use standard formatting for dates, checkboxes, currency
- Include [SPECIFIC_CALCULATIONS] if needed (e.g., profit calculations, aging analysis)

**Special Requirements:**
- [ANY_SPECIFIC_FEATURES] (e.g., grouping, subtotals, conditional formatting)

Please use the FreightMas report utilities framework from utils/report_utils.py and follow the established patterns from existing reports.
```

## 🛠️ Example Usage

### Example 1: Truck Performance Report
```
Create a new report for trucking_service called "Truck Performance Analysis" with the following requirements:

**Report Details:**
- Report Name: Truck Performance Analysis
- Service Module: trucking_service
- DocType: Truck Trip
- Report Type: Query Report

**Required Columns:**
- Standard columns: job_date, customer, reference, origin, destination, status
- Custom columns: truck_number, driver_name, trip_distance, fuel_consumed, trip_duration

**Filters Required:**
- Date range (from_date, to_date)
- Customer filter
- Truck filter
- Driver filter
- Route filter

**Data Processing:**
- Use standard formatting for dates, checkboxes, currency
- Include fuel efficiency calculations (distance/fuel_consumed)
- Calculate average trip time

**Special Requirements:**
- Group by truck number
- Show subtotals for total distance and fuel per truck
- Color-code status field (green for completed, yellow for in-progress)

Please use the FreightMas report utilities framework from utils/report_utils.py and follow the established patterns from existing reports.
```

### Example 2: Container Demurrage Report
```
Create a new report for clearing_service called "Container Demurrage Analysis" with the following requirements:

**Report Details:**
- Report Name: Container Demurrage Analysis
- Service Module: clearing_service
- DocType: Clearing Job
- Report Type: Query Report

**Required Columns:**
- Standard columns: job_id, job_date, customer, bl_number, consignee
- Custom columns: container_number, discharge_date, pickup_date, demurrage_days, demurrage_amount

**Filters Required:**
- Date range (from_date, to_date)
- Customer filter
- Status filter
- Shipping line filter
- Container type filter

**Data Processing:**
- Use standard formatting for dates, checkboxes, currency
- Calculate demurrage days (pickup_date - discharge_date - free_days)
- Calculate demurrage amounts

**Special Requirements:**
- Highlight overdue containers in red
- Show summary totals
- Export functionality for Excel and PDF

Please use the FreightMas report utilities framework from utils/report_utils.py and follow the established patterns from existing reports.
```

## 📚 Framework Reference

### Available Standard Columns
The following standard columns are available in `get_standard_columns()`:

- `job_id` - Job ID with link to document
- `job_date` - Formatted job date
- `customer` - Customer link
- `customer_name` - Customer name as text
- `reference` - Customer reference (width: 160px)
- `direction` - Import/Export direction
- `status` - Job status
- `bl_number` - Bill of Lading number (width: 160px)
- `shipper` - Shipper customer (width: 160px)
- `consignee` - Consignee customer (width: 160px)
- `origin` - Port of loading
- `destination` - Destination port
- `eta/etd/ata/atd` - Various date fields
- `estimated_revenue/cost/profit` - Financial fields
- `cargo_description` - Cargo description
- Checkbox fields: `is_bl_received`, `is_bl_confirmed`, etc.

### Standard Utilities Available

```python
from freightmas.utils.report_utils import (
    # Column definitions
    get_standard_columns,
    
    # Data processing
    process_job_data,
    build_job_filters,
    
    # Formatting functions
    format_date,
    format_checkbox,
    combine_direction_shipment,
    
    # Validation
    validate_date_filters,
    
    # Base class
    ReportBuilder,
    
    # Status options
    get_standard_status_options,
    
    # File naming
    get_report_filename
)
```

### Standard Report Structure

```python
# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from freightmas.utils.report_utils import (
    get_standard_columns,
    build_job_filters,
    process_job_data,
    validate_date_filters
)

def get_columns():
    """Get column definitions using standard utilities."""
    standard_cols = get_standard_columns()
    
    columns = [
        standard_cols["job_id"],
        standard_cols["job_date"],
        standard_cols["customer"],
        standard_cols["customer_reference"],
        # Add custom columns as needed
    ]
    
    return columns

def execute(filters=None):
    """Main execution function using standardized utilities."""
    # Validate filters
    filters = validate_date_filters(filters or {})
    
    # Get columns
    columns = get_columns()
    
    # Build database filters
    job_filters = build_job_filters(filters, "Your DocType")
    
    # Get data from database
    jobs = frappe.get_all(
        "Your DocType",
        filters=job_filters,
        fields=["field1", "field2", "field3"],
        order_by="date_created desc"
    )
    
    # Process data with standard formatting
    data = process_job_data(jobs, service_type="your_service")
    
    return columns, data
```

### JavaScript Structure

```javascript
frappe.query_reports["Your Report Name"] = {
    "filters": [
        // Use standard date range filter pattern
        {
            "fieldname": "date_range",
            "label": __("Date Range"),
            "fieldtype": "Select",
            "options": "\nToday\nYesterday\nThis Week\nLast Week\nThis Month\nLast Month\nThis Year\nLast Year\nCustom",
            "default": "This Month",
            "on_change": function() {
                apply_date_range_filter();
            }
        },
        // Standard from/to date filters
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
        // Standard filters
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
        // Setup standard buttons
        if (window.FreightmasReportUtils && window.FreightmasReportUtils.setup_standard_export_buttons) {
            window.FreightmasReportUtils.setup_standard_export_buttons(report, "Your Report Name");
        }
    }
};

// Include date range helper function
function apply_date_range_filter() {
    // Standard date range logic
}
```

## 🎯 Benefits of Using This Framework

1. **Consistency** - All reports follow the same patterns
2. **Maintainability** - Changes to utilities affect all reports
3. **Code Reduction** - Minimal code duplication
4. **Standard UI** - Consistent user experience across all reports
5. **Easy Extension** - Simple to add new features globally

## 📱 Standard Button Layout

All FreightMas reports follow this button layout pattern:

```
[Export ▼] [Clear Filters] [Actions ▼] [Refresh]
```

- **Export Dropdown**: Contains "Export to Excel" and "Export to PDF" options
- **Clear Filters**: Standalone button that resets all filters to defaults
- **Actions Dropdown**: Standard Frappe actions (Menu, Set Columns, etc.)
- **Refresh**: Standard refresh button

This layout is automatically implemented when using `FreightmasReportUtils.setup_standard_export_buttons()`.

## 📝 File Locations

- **Utilities**: `freightmas/utils/report_utils.py`
- **JavaScript**: `freightmas/public/js/report_commons.js`
- **Report Examples**: 
  - `forwarding_service/report/forwarding_job_register/`
  - `clearing_service/report/clearing_job_tracking/`
  - `trucking_service/report/` (for future reports)

---

*Last Updated: November 11, 2025*
*Framework Version: 1.0*