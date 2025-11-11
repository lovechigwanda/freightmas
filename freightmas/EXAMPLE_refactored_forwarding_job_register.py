# Example: Refactored Forwarding Job Register using Report Utilities
"""
This is an example of how to refactor the existing Forwarding Job Register report
using the new report utilities for consistency and reduced code duplication.
"""

from __future__ import unicode_literals
from freightmas.utils.report_utils import (
    ReportBuilder, 
    build_job_filters, 
    process_job_data,
    validate_date_filters
)
import frappe


class ForwardingJobRegisterReport(ReportBuilder):
    """
    Refactored Forwarding Job Register using the new ReportBuilder base class.
    """
    
    def __init__(self):
        super().__init__(doctype="Forwarding Job", service_type="forwarding")
    
    def get_columns(self):
        """Define columns using standard column definitions."""
        # Use base columns for common fields
        columns = self.get_base_columns([
            "job_id", "job_date", "customer", "reference", "direction", 
            "origin", "destination", "bl_number", "eta", 
            "estimated_revenue", "estimated_cost", "estimated_profit", "status"
        ])
        
        # Customize specific columns for forwarding jobs
        # Update job_id column to link to Forwarding Job
        columns[0]["options"] = "Forwarding Job"
        
        return columns
    
    def execute(self, filters=None):
        """Main execution function."""
        # Validate and normalize filters
        filters = validate_date_filters(filters or {})
        
        # Get columns
        columns = self.get_columns()
        
        # Build database filters
        job_filters = build_job_filters(filters, "Forwarding Job")
        
        # Get data from database
        jobs = frappe.get_all(
            "Forwarding Job",
            filters=job_filters,
            fields=[
                "name", "date_created", "customer", "customer_reference", 
                "direction", "shipment_mode", "port_of_loading", "destination", 
                "bl_number", "eta", "total_quoted_revenue_base", 
                "total_quoted_cost_base", "total_quoted_profit_base", "status"
            ],
            order_by="date_created desc"
        )
        
        # Process data using standard utilities
        data = process_job_data(jobs, service_type="forwarding")
        
        return columns, data


# Main execute function for backward compatibility
def execute(filters=None):
    """
    Main execute function called by Frappe framework.
    """
    report = ForwardingJobRegisterReport()
    return report.execute(filters)


def get_columns():
    """
    Backward compatibility function.
    """
    report = ForwardingJobRegisterReport()
    return report.get_columns()


def format_date(date_str):
    """
    Backward compatibility function - now handled by report_utils.
    """
    from freightmas.utils.report_utils import format_date as util_format_date
    return util_format_date(date_str)