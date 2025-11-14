# FreightMas Report Utilities
"""
Common utilities for FreightMas reports to ensure consistency and reduce code duplication.
"""
import frappe
from frappe import _
from frappe.utils import formatdate, getdate


def format_checkbox(value):
    """
    Convert checkbox field values to user-friendly Yes/No text.
    
    Args:
        value: The checkbox value (1, 0, True, False, etc.)
        
    Returns:
        "Yes" or "No" string
    """
    if value in [1, True, "1", "true", "True"]:
        return "Yes"
    else:
        return "No"


def format_date(date_str, format_type="dd-MMM-yy"):
    """
    Standard date formatting function for all reports.
    
    Args:
        date_str: Date string or date object
        format_type: Format string (default: "dd-MMM-yy")
        
    Returns:
        Formatted date string or empty string if no date
    """
    if not date_str:
        return ""
    try:
        return formatdate(date_str, format_type)
    except Exception:
        return str(date_str) if date_str else ""


def get_standard_columns():
    """
    Returns dictionary of standard column definitions for common fields.
    """
    return {
    "job_id": {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        "job_date": {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        "customer": {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        "customer_name": {"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
        "reference": {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 160},
        "direction": {"label": "Direction", "fieldname": "direction", "fieldtype": "Data", "width": 120},
        "status": {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
        "currency": {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 80},
        "conversion_rate": {"label": "Conv. Rate", "fieldname": "conversion_rate", "fieldtype": "Float", "width": 80},
        "bl_number": {"label": "BL Number", "fieldname": "bl_number", "fieldtype": "Data", "width": 160},
        "eta": {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 100},
        "etd": {"label": "ETD", "fieldname": "etd", "fieldtype": "Data", "width": 100},
        "ata": {"label": "ATA", "fieldname": "ata", "fieldtype": "Data", "width": 100},
        "atd": {"label": "ATD", "fieldname": "atd", "fieldtype": "Data", "width": 100},
        "origin": {"label": "Origin", "fieldname": "port_of_loading", "fieldtype": "Link", "options": "Port", "width": 120},
        "destination": {"label": "Destination", "fieldname": "destination", "fieldtype": "Link", "options": "Port", "width": 120},
        "estimated_revenue": {"label": "Est. Rev", "fieldname": "total_quoted_revenue_base", "fieldtype": "Currency", "width": 110},
        "estimated_cost": {"label": "Est. Cost", "fieldname": "total_quoted_cost_base", "fieldtype": "Currency", "width": 110},
        "estimated_profit": {"label": "Est. Prft", "fieldname": "total_quoted_profit_base", "fieldtype": "Currency", "width": 110},
        "completed_on": {"label": "Completed", "fieldname": "completed_on", "fieldtype": "Data", "width": 110},
        "created_by": {"label": "Created By", "fieldname": "created_by", "fieldtype": "Data", "width": 110},
        "company": {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100},
        "shipper": {"label": "Shipper", "fieldname": "shipper", "fieldtype": "Link", "options": "Customer", "width": 160},
        "consignee": {"label": "Consignee", "fieldname": "consignee", "fieldtype": "Link", "options": "Customer", "width": 160},
        "cargo_description": {"label": "Cargo Desc.", "fieldname": "cargo_description", "fieldtype": "Data", "width": 150, "align": "left"},
        # Checkbox fields as Data type to show Yes/No text
        "is_bl_received": {"label": "BL Recvd", "fieldname": "is_bl_received", "fieldtype": "Data", "width": 80},
        "is_bl_confirmed": {"label": "BL Confmd", "fieldname": "is_bl_confirmed", "fieldtype": "Data", "width": 80},
        "is_hazardous": {"label": "Hazardous", "fieldname": "is_hazardous", "fieldtype": "Data", "width": 80},
        "to_be_returned": {"label": "To Return", "fieldname": "to_be_returned", "fieldtype": "Data", "width": 80},
        "is_loaded": {"label": "Loaded", "fieldname": "is_loaded", "fieldtype": "Data", "width": 80},
        "is_returned": {"label": "Returned", "fieldname": "is_returned", "fieldtype": "Data", "width": 80},
        "is_loaded_on_vessel": {"label": "On Vessel", "fieldname": "is_loaded_on_vessel", "fieldtype": "Data", "width": 80},
    }


def build_job_filters(filters, doctype, date_field="date_created"):
    """
    Build standard filter conditions for job-type documents.
    
    Args:
        filters: Dictionary of filter values
        doctype: Document type name
        date_field: Name of date field for date range filtering
        
    Returns:
        Dictionary of filter conditions for frappe.get_all()
    """
    job_filters = {}
    
    if filters.get("from_date") and filters.get("to_date"):
        job_filters[date_field] = ["between", [filters["from_date"], filters["to_date"]]]
    elif filters.get("date_from") and filters.get("date_to"):  # Alternative naming
        job_filters[date_field] = ["between", [filters["date_from"], filters["date_to"]]]
    
    if filters.get("customer"):
        job_filters["customer"] = filters["customer"]
    
    if filters.get("customer_reference"):
        job_filters["customer_reference"] = ["like", f"%{filters['customer_reference']}%"]
    
    if filters.get("status"):
        job_filters["status"] = filters["status"]
    
    if filters.get("direction"):
        job_filters["direction"] = filters["direction"]
    
    if filters.get("company"):
        job_filters["company"] = filters["company"]
        
    return job_filters


def combine_direction_shipment(row):
    """
    Combine shipment_mode and direction for display.
    
    Args:
        row: Data row dictionary
        
    Returns:
        Combined direction string
    """
    shipment_mode = row.get("shipment_mode", "")
    direction = row.get("direction", "")
    
    if shipment_mode and direction:
        return f"{shipment_mode} {direction}"
    elif shipment_mode:
        return shipment_mode
    elif direction:
        return direction
    else:
        return ""


def get_standard_status_options():
    """
    Returns standard status options for different document types.
    """
    return {
        "job_status": ["", "Draft", "In Progress", "Completed", "Cancelled"],
        "container_status": ["", "In Port", "Not Returned", "Returned", "Delivered"],
        "export_container_status": ["", "Not Yet Picked", "Not Yet Gated In", "In Port", "Loaded on Vessel"],
        "direction_options": ["", "Import", "Export"],
        "shipment_mode": ["", "Sea", "Air", "Road", "Rail"],
    }


def process_job_data(jobs, service_type="forwarding"):
    """
    Process job data with standard formatting and calculations.
    
    Args:
        jobs: List of job dictionaries
        service_type: Type of service (forwarding, clearing, trucking, etc.)
        
    Returns:
        List of processed job data
    """
    data = []
    
    for job in jobs:
        # Standard date formatting
        processed_job = {
            "name": job.get("name", ""),
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "direction": combine_direction_shipment(job),
            "status": job.get("status", ""),
            "currency": job.get("currency", ""),
            "conversion_rate": job.get("conversion_rate", 1.0),
        }
        
        # Service-specific processing
        if service_type in ["forwarding", "clearing"]:
            processed_job.update({
                "port_of_loading": job.get("port_of_loading", ""),
                "destination": job.get("destination", ""),
                "bl_number": job.get("bl_number", ""),
                "eta": format_date(job.get("eta")),
                "etd": format_date(job.get("etd")),
                "shipper": job.get("shipper", ""),
                "consignee": job.get("consignee", ""),
                "cargo_description": job.get("cargo_description", ""),
            })
            
        # Financial fields
        processed_job.update({
            "total_quoted_revenue_base": job.get("total_quoted_revenue_base", 0),
            "total_quoted_cost_base": job.get("total_quoted_cost_base", 0),
            "total_quoted_profit_base": job.get("total_quoted_profit_base", 0),
            "completed_on": format_date(job.get("completed_on")),
        })
        
        # Extended fields if available
        if job.get("booking_date"):
            processed_job["booking_date"] = format_date(job.get("booking_date"))
        if job.get("cargo_ready_date"):
            processed_job["cargo_ready_date"] = format_date(job.get("cargo_ready_date"))
        if job.get("delivery_date"):
            processed_job["delivery_date"] = format_date(job.get("delivery_date"))
        if job.get("ata"):
            processed_job["ata"] = format_date(job.get("ata"))
        if job.get("atd"):
            processed_job["atd"] = format_date(job.get("atd"))
            
        # Convert checkbox fields to Yes/No
        checkbox_fields = [
            "is_bl_received", "is_bl_confirmed", "is_hazardous", 
            "to_be_returned", "is_loaded", "is_returned", 
            "is_loaded_on_vessel"
        ]
        
        for field in checkbox_fields:
            if field in job:
                processed_job[field] = format_checkbox(job.get(field))
            
        data.append(processed_job)
    
    return data


def get_report_filename(report_name, file_type, party=None, timestamp=None):
    """
    Generate standard filename for reports.
    
    Args:
        report_name: Name of the report
        file_type: File extension (xlsx, pdf, etc.)
        party: Optional party name for personalized reports
        timestamp: Optional timestamp (will use current if not provided)
        
    Returns:
        Formatted filename
    """
    if not timestamp:
        timestamp = frappe.utils.now_datetime().strftime("%Y%m%d_%H%M")
    
    # Clean report name for filename
    clean_name = report_name.replace(" ", "_").replace("/", "_")
    
    if party:
        return f"{clean_name}_{party}_{timestamp}.{file_type}"
    else:
        return f"{clean_name}_{timestamp}.{file_type}"


def validate_date_filters(filters):
    """
    Validate and normalize date filters.
    
    Args:
        filters: Dictionary of filters
        
    Returns:
        Dictionary with validated date filters
    """
    validated = filters.copy()
    
    # Normalize date field names
    if "date_from" in validated and "from_date" not in validated:
        validated["from_date"] = validated["date_from"]
    if "date_to" in validated and "to_date" not in validated:
        validated["to_date"] = validated["date_to"]
    
    # Validate date ranges
    if validated.get("from_date") and validated.get("to_date"):
        try:
            from_date = getdate(validated["from_date"])
            to_date = getdate(validated["to_date"])
            
            if from_date > to_date:
                frappe.throw(_("From Date cannot be greater than To Date"))
                
        except Exception:
            frappe.throw(_("Invalid date format in filters"))
    
    return validated


class ReportBuilder:
    """
    Base class for building consistent reports.
    """
    
    def __init__(self, doctype, service_type="generic"):
        self.doctype = doctype
        self.service_type = service_type
        self.standard_columns = get_standard_columns()
        self.status_options = get_standard_status_options()
    
    def get_base_columns(self, column_keys):
        """
        Get base columns using standard definitions.
        
        Args:
            column_keys: List of column keys from standard_columns
            
        Returns:
            List of column definitions
        """
        columns = []
        for key in column_keys:
            if key in self.standard_columns:
                columns.append(self.standard_columns[key].copy())
            else:
                frappe.log_error(f"Unknown column key: {key}")
        
        return columns
    
    def add_custom_column(self, columns, label, fieldname, fieldtype="Data", width=120, **kwargs):
        """
        Add custom column to columns list.
        """
        column_def = {
            "label": label,
            "fieldname": fieldname,
            "fieldtype": fieldtype,
            "width": width
        }
        column_def.update(kwargs)
        columns.append(column_def)
        return columns
    
    def execute(self, filters=None):
        """
        Override this method in subclasses.
        """
        raise NotImplementedError("Subclasses must implement execute method")