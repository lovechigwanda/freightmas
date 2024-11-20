# Copyright (c) 2024, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe.utils import flt

def execute(filters=None):
    if not filters or not filters.get("trip_name"):
        frappe.throw("This report requires a specific trip to be passed as a filter.")

    trip_name = filters.get("trip_name")
    trip = frappe.get_doc("Trip", trip_name)

    columns = get_columns()
    data = get_data(trip)

    return columns, data


def get_columns():
    return [
        {"fieldname": "party", "label": "Party", "fieldtype": "Data", "width": 150},
        {"fieldname": "charge_type", "label": "Charge Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "total_estimated", "label": "Total Estimated", "fieldtype": "Currency", "width": 120},
        {"fieldname": "total_invoiced", "label": "Total Invoiced", "fieldtype": "Currency", "width": 120},
        {"fieldname": "difference", "label": "Difference", "fieldtype": "Currency", "width": 120},
    ]


def get_filters():
    return [
        {
            "fieldname": "trip_name",
            "label": "Trip",
            "fieldtype": "Link",
            "options": "Trip",
            "reqd": 1,
        }
    ]


def get_data(trip):
    data = []

    # Revenue Charges (Receivable Party)
    receivable_summary = summarize_charges(trip.trip_revenue_charges, "receivable_party", "Sales Invoice")
    for party, summary in receivable_summary.items():
        data.append({
            "party": party,
            "charge_type": "Revenue",
            "total_estimated": summary["total_estimated"],
            "total_invoiced": summary["total_invoiced"],
            "difference": summary["total_invoiced"] - summary["total_estimated"],
        })

    # Cost Charges (Payable Party)
    payable_summary = summarize_charges(trip.trip_cost_charges, "payable_party", "Purchase Invoice")
    for party, summary in payable_summary.items():
        data.append({
            "party": party,
            "charge_type": "Cost",
            "total_estimated": summary["total_estimated"],
            "total_invoiced": summary["total_invoiced"],
            "difference": summary["total_invoiced"] - summary["total_estimated"],
        })

    # Add overall summary row
    total_revenue = sum(item["total_estimated"] for item in data if item["charge_type"] == "Revenue")
    total_cost = sum(item["total_estimated"] for item in data if item["charge_type"] == "Cost")
    total_actual_revenue = sum(item["total_invoiced"] for item in data if item["charge_type"] == "Revenue")
    total_actual_cost = sum(item["total_invoiced"] for item in data if item["charge_type"] == "Cost")

    estimated_profit = total_revenue - total_cost
    actual_profit = total_actual_revenue - total_actual_cost

    data.append({
        "party": "Total",
        "charge_type": "Summary",
        "total_estimated": estimated_profit,
        "total_invoiced": actual_profit,
        "difference": actual_profit - estimated_profit,
    })

    return data


def summarize_charges(charges, party_field, invoice_field):
    """
    Summarize charges by party.
    """
    summary = {}
    for charge in charges:
        party = getattr(charge, party_field)
        if not party:
            continue

        if party not in summary:
            summary[party] = {"total_estimated": 0, "total_invoiced": 0}

        # Add estimated charge
        summary[party]["total_estimated"] += flt(charge.rate)

        # Add invoiced amount if available
        if getattr(charge, invoice_field):
            invoice_total = frappe.db.get_value(
                "Sales Invoice" if invoice_field == "Sales Invoice" else "Purchase Invoice",
                getattr(charge, invoice_field),
                "total"
            ) or 0
            summary[party]["total_invoiced"] += invoice_total

    return summary
