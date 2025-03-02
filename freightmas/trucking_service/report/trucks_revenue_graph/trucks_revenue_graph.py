# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe.utils import today, get_first_day, get_last_day

def execute(filters=None):
    """
    Graph Report: Trucks with Trips in Current Month
    X-Axis: Truck Names
    Y-Axis: Estimated Revenue vs. Actual Booked Revenue
    """
    start_date = get_first_day(today())
    end_date = get_last_day(today())

    # Fetch estimated revenue per truck for the current month
    estimated_revenue_data = frappe.db.sql(
        """
        SELECT t.truck, COALESCE(SUM(rc.total_amount), 0) AS total_amount
        FROM `tabTrip` t
        JOIN `tabTrip Revenue Charges` rc ON rc.parent = t.name
        WHERE t.docstatus < 2 AND t.date_created BETWEEN %s AND %s
        GROUP BY t.truck
        """, (start_date, end_date), as_dict=True
    )

    # Fetch actual invoiced revenue per truck for the current month
    invoiced_revenue_data = frappe.db.sql(
        """
        SELECT t.truck, COALESCE(SUM(rc.total_amount), 0) AS total_amount
        FROM `tabTrip` t
        JOIN `tabTrip Revenue Charges` rc ON rc.parent = t.name
        WHERE rc.is_invoiced = 1 AND t.docstatus < 2 
        AND t.date_created BETWEEN %s AND %s
        GROUP BY t.truck
        """, (start_date, end_date), as_dict=True
    )

    # Convert results to dictionaries for easy lookup
    estimated_revenue = {row["truck"]: row.get("total_amount", 0) for row in estimated_revenue_data}
    invoiced_revenue = {row["truck"]: row.get("total_amount", 0) for row in invoiced_revenue_data}

    # Prepare data for graph
    trucks = list(set(estimated_revenue.keys()) | set(invoiced_revenue.keys()))

    data = []
    for truck in trucks:
        data.append({
            "Truck": truck,
            "Estimated Revenue": estimated_revenue.get(truck, 0),
            "Actual Revenue": invoiced_revenue.get(truck, 0)
        })

    # Define Report Columns
    columns = [
        {"label": "Truck", "fieldname": "Truck", "fieldtype": "Link", "options": "Truck"},
        {"label": "Estimated Revenue", "fieldname": "Estimated Revenue", "fieldtype": "Currency"},
        {"label": "Actual Revenue", "fieldname": "Actual Revenue", "fieldtype": "Currency"}
    ]

    return columns, data
