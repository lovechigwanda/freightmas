# Copyright (c) 2024, Lovech Technologies Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, date_diff, formatdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    # Build conditions and parameters for parameterized query
    conditions = ["docstatus IN (0, 1)"]
    params = {}
    
    if filters.get("from_date"):
        conditions.append("date_created >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    
    if filters.get("to_date"):
        conditions.append("date_created <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        params["customer"] = filters["customer"]
    
    if filters.get("customer_reference"):
        conditions.append("customer_reference LIKE %(customer_reference)s")
        params["customer_reference"] = "%" + filters["customer_reference"] + "%"

    where_clause = " AND ".join(conditions)

    # Get forwarding jobs data
    jobs = frappe.db.sql("""
        SELECT name, date_created, customer, customer_reference, 
               port_of_discharge, eta, ata, discharge_date, cargo_count
        FROM `tabForwarding Job`
        WHERE {where_clause}
        ORDER BY date_created DESC
    """.format(where_clause=where_clause), params, as_dict=True)

    # Process data with incoming cargo logic
    today = getdate()
    
    for job in jobs:
        eta = job.get("eta")
        ata = job.get("ata")
        discharge_date = job.get("discharge_date")
        
        # Skip jobs that are already discharged
        if discharge_date:
            continue
            
        status = ""
        days = ""
        
        if ata and not discharge_date:
            # Vessel arrived but cargo not discharged
            status = "Awaiting Discharge"
            days = "0"
        elif not ata:
            # Vessel not arrived yet
            if eta:
                eta_date = getdate(eta)
                days_diff = date_diff(eta_date, today)
                
                if days_diff > 0:
                    status = "En Route"
                    days = f"+{days_diff}"
                elif days_diff == 0:
                    status = "Due Today"
                    days = "0"
                else:
                    status = "Overdue Arrival"
                    days = str(days_diff)
            else:
                status = "No ETA"
                days = ""
        
        # Format data
        data.append({
            "name": job.get("name", ""),
            "date_created": format_date(job.get("date_created")),
            "customer": job.get("customer", ""),
            "customer_reference": job.get("customer_reference", ""),
            "port_of_discharge": job.get("port_of_discharge", ""),
            "eta": format_date(job.get("eta")),
            "ata": format_date(job.get("ata")),
            "cargo_count": job.get("cargo_count", ""),
            "status": status,
            "days": days,
        })
    
    return columns, data

def get_columns():
    return [
        {"label": "Job ID", "fieldname": "name", "fieldtype": "Link", "options": "Forwarding Job", "width": 140},
        {"label": "Job Date", "fieldname": "date_created", "fieldtype": "Data", "width": 100},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Reference", "fieldname": "customer_reference", "fieldtype": "Data", "width": 140},
        {"label": "Cargo", "fieldname": "cargo_count", "fieldtype": "Data", "width": 80},
        {"label": "Disch Port", "fieldname": "port_of_discharge", "fieldtype": "Link", "options": "Port", "width": 120},
        {"label": "ETA", "fieldname": "eta", "fieldtype": "Data", "width": 100},
        {"label": "ATA", "fieldname": "ata", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": "Days", "fieldname": "days", "fieldtype": "Data", "width": 80},
    ]

def format_date(date_value):
    """Format date string to dd-MMM-yy format."""
    if not date_value:
        return ""
    try:
        return formatdate(date_value, "dd-MMM-yy")
    except Exception:
        return date_value