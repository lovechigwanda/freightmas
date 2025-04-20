# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.pdf import get_pdf
from frappe.utils import nowdate

def execute(filters=None):
    if not filters:
        filters = {}

    query = """
    SELECT
      name AS trip_id,
      date_created,
      truck,
      customer,
      route,
      workflow_state AS status,
      current_trip_milestone AS milestone,
      current_milestone_comment AS comment,
      updated_on
    FROM `tabTrip`
    WHERE workflow_state NOT IN ('Closed')
    """
    
    conditions = []
    if filters.get("start_date"):
        conditions.append("date_created >= %(start_date)s")
    if filters.get("end_date"):
        conditions.append("date_created <= %(end_date)s")
    if filters.get("client"):
        conditions.append("customer = %(client)s")
    
    if conditions:
        query += " AND " + " AND ".join(conditions)
    
    data = frappe.db.sql(query, filters, as_dict=True)
    
    html_content = frappe.render_template("""
    <h2 style="text-align: center;">Active Trip Report 2</h2>
    <p style="text-align: center; font-size: 14px;">Generated on {{ nowdate }}</p>
    <table style="width: 100%; border-collapse: collapse; border: 1px solid black;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th style="border: 1px solid black; padding: 5px;">Trip ID</th>
                <th style="border: 1px solid black; padding: 5px;">Date Created</th>
                <th style="border: 1px solid black; padding: 5px;">Truck</th>
                <th style="border: 1px solid black; padding: 5px;">Customer</th>
                <th style="border: 1px solid black; padding: 5px;">Route</th>
                <th style="border: 1px solid black; padding: 5px;">Status</th>
                <th style="border: 1px solid black; padding: 5px;">Milestone</th>
            </tr>
        </thead>
        <tbody>
            {% for row in data %}
            <tr>
                <td style="border: 1px solid black; padding: 5px;">{{ row.trip_id }}</td>
                <td style="border: 1px solid black; padding: 5px;">{{ row.date_created }}</td>
                <td style="border: 1px solid black; padding: 5px;">{{ row.truck }}</td>
                <td style="border: 1px solid black; padding: 5px;">{{ row.customer }}</td>
                <td style="border: 1px solid black; padding: 5px;">{{ row.route }}</td>
                <td style="border: 1px solid black; padding: 5px;">{{ row.status }}</td>
                <td style="border: 1px solid black; padding: 5px;">{{ row.milestone }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    """, {"data": data, "nowdate": nowdate()})
    
    pdf = get_pdf(html_content)
    frappe.local.response.filename = "Active_Trip_Report_2.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"

    return [], []
