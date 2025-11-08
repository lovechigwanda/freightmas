"""
Utility functions for Forwarding Job costing and charge calculations.
These functions provide data aggregation for reports and print formats.
"""

import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_all_charges_summary(job_name):
    """
    Get a summary of all charges (quoted, working, invoiced) for a forwarding job.
    
    Returns a dictionary keyed by charge name with aggregated amounts:
    {
        'charge_name': {
            'quoted_revenue': amount,
            'quoted_cost': amount,
            'working_revenue': amount,
            'working_cost': amount,
            'invoiced_revenue': amount,
            'invoiced_cost': amount
        }
    }
    """
    try:
        doc = frappe.get_doc('Forwarding Job', job_name)
    except frappe.DoesNotExistError:
        return {}
    
    charges_summary = {}
    
    # Process planned/quoted charges
    if hasattr(doc, 'forwarding_costing_charges') and doc.forwarding_costing_charges:
        for row in doc.forwarding_costing_charges:
            charge_name = row.charge
            if charge_name not in charges_summary:
                charges_summary[charge_name] = {
                    'quoted_revenue': 0,
                    'quoted_cost': 0,
                    'working_revenue': 0,
                    'working_cost': 0,
                    'invoiced_revenue': 0,
                    'invoiced_cost': 0
                }
            charges_summary[charge_name]['quoted_revenue'] += flt(row.revenue_amount or 0)
            charges_summary[charge_name]['quoted_cost'] += flt(row.cost_amount or 0)
    
    # Process working/actual revenue charges
    if hasattr(doc, 'forwarding_revenue_charges') and doc.forwarding_revenue_charges:
        for row in doc.forwarding_revenue_charges:
            charge_name = row.charge
            if charge_name not in charges_summary:
                charges_summary[charge_name] = {
                    'quoted_revenue': 0,
                    'quoted_cost': 0,
                    'working_revenue': 0,
                    'working_cost': 0,
                    'invoiced_revenue': 0,
                    'invoiced_cost': 0
                }
            charges_summary[charge_name]['working_revenue'] += flt(row.revenue_amount or 0)
    
    # Process working/actual cost charges
    if hasattr(doc, 'forwarding_cost_charges') and doc.forwarding_cost_charges:
        for row in doc.forwarding_cost_charges:
            charge_name = row.charge
            if charge_name not in charges_summary:
                charges_summary[charge_name] = {
                    'quoted_revenue': 0,
                    'quoted_cost': 0,
                    'working_revenue': 0,
                    'working_cost': 0,
                    'invoiced_revenue': 0,
                    'invoiced_cost': 0
                }
            charges_summary[charge_name]['working_cost'] += flt(row.cost_amount or 0)
    
    # Process invoiced amounts from Sales Invoices (revenue)
    sales_invoices = frappe.get_all(
        'Sales Invoice',
        filters={'forwarding_job_reference': job_name, 'docstatus': 1},
        fields=['name']
    )
    
    for si in sales_invoices:
        si_doc = frappe.get_doc('Sales Invoice', si.name)
        if hasattr(si_doc, 'items') and si_doc.items:
            for item in si_doc.items:
                charge_name = item.item_code or item.item_name
                if charge_name not in charges_summary:
                    charges_summary[charge_name] = {
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                charges_summary[charge_name]['invoiced_revenue'] += flt(item.amount or 0)
    
    # Process invoiced amounts from Purchase Invoices (cost)
    purchase_invoices = frappe.get_all(
        'Purchase Invoice',
        filters={'forwarding_job_reference': job_name, 'docstatus': 1},
        fields=['name']
    )
    
    for pi in purchase_invoices:
        pi_doc = frappe.get_doc('Purchase Invoice', pi.name)
        if hasattr(pi_doc, 'items') and pi_doc.items:
            for item in pi_doc.items:
                charge_name = item.item_code or item.item_name
                if charge_name not in charges_summary:
                    charges_summary[charge_name] = {
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                charges_summary[charge_name]['invoiced_cost'] += flt(item.amount or 0)
    
    return charges_summary


@frappe.whitelist()
def get_all_parties_summary(job_name):
    """
    Get a summary of all parties (customers/suppliers) and their charge amounts.
    
    Returns a dictionary keyed by party name with:
    {
        'party_name': {
            'party_type': 'Customer' or 'Supplier',
            'quoted_revenue': amount,
            'quoted_cost': amount,
            'working_revenue': amount,
            'working_cost': amount,
            'invoiced_revenue': amount,
            'invoiced_cost': amount
        }
    }
    """
    try:
        doc = frappe.get_doc('Forwarding Job', job_name)
    except frappe.DoesNotExistError:
        return {}
    
    parties_summary = {}
    
    # Process planned charges - customers
    if hasattr(doc, 'forwarding_costing_charges') and doc.forwarding_costing_charges:
        for row in doc.forwarding_costing_charges:
            if row.customer:
                if row.customer not in parties_summary:
                    parties_summary[row.customer] = {
                        'party_type': 'Customer',
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                parties_summary[row.customer]['quoted_revenue'] += flt(row.revenue_amount or 0)
            
            # Process planned charges - suppliers
            if row.supplier:
                if row.supplier not in parties_summary:
                    parties_summary[row.supplier] = {
                        'party_type': 'Supplier',
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                parties_summary[row.supplier]['quoted_cost'] += flt(row.cost_amount or 0)
    
    # Process working revenue charges - customers
    if hasattr(doc, 'forwarding_revenue_charges') and doc.forwarding_revenue_charges:
        for row in doc.forwarding_revenue_charges:
            if row.customer:
                if row.customer not in parties_summary:
                    parties_summary[row.customer] = {
                        'party_type': 'Customer',
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                parties_summary[row.customer]['working_revenue'] += flt(row.revenue_amount or 0)
    
    # Process working cost charges - suppliers
    if hasattr(doc, 'forwarding_cost_charges') and doc.forwarding_cost_charges:
        for row in doc.forwarding_cost_charges:
            if row.supplier:
                if row.supplier not in parties_summary:
                    parties_summary[row.supplier] = {
                        'party_type': 'Supplier',
                        'quoted_revenue': 0,
                        'quoted_cost': 0,
                        'working_revenue': 0,
                        'working_cost': 0,
                        'invoiced_revenue': 0,
                        'invoiced_cost': 0
                    }
                parties_summary[row.supplier]['working_cost'] += flt(row.cost_amount or 0)
    
    # Process invoiced revenue from Sales Invoices
    sales_invoices = frappe.get_all(
        'Sales Invoice',
        filters={'forwarding_job_reference': job_name, 'docstatus': 1},
        fields=['name', 'customer']
    )
    
    for si in sales_invoices:
        customer = si.customer
        if customer not in parties_summary:
            parties_summary[customer] = {
                'party_type': 'Customer',
                'quoted_revenue': 0,
                'quoted_cost': 0,
                'working_revenue': 0,
                'working_cost': 0,
                'invoiced_revenue': 0,
                'invoiced_cost': 0
            }
        
        si_doc = frappe.get_doc('Sales Invoice', si.name)
        if hasattr(si_doc, 'items') and si_doc.items:
            for item in si_doc.items:
                parties_summary[customer]['invoiced_revenue'] += flt(item.amount or 0)
    
    # Process invoiced cost from Purchase Invoices
    purchase_invoices = frappe.get_all(
        'Purchase Invoice',
        filters={'forwarding_job_reference': job_name, 'docstatus': 1},
        fields=['name', 'supplier']
    )
    
    for pi in purchase_invoices:
        supplier = pi.supplier
        if supplier not in parties_summary:
            parties_summary[supplier] = {
                'party_type': 'Supplier',
                'quoted_revenue': 0,
                'quoted_cost': 0,
                'working_revenue': 0,
                'working_cost': 0,
                'invoiced_revenue': 0,
                'invoiced_cost': 0
            }
        
        pi_doc = frappe.get_doc('Purchase Invoice', pi.name)
        if hasattr(pi_doc, 'items') and pi_doc.items:
            for item in pi_doc.items:
                parties_summary[supplier]['invoiced_cost'] += flt(item.amount or 0)
    
    return parties_summary


@frappe.whitelist()
def get_job_totals_summary(job_name):
    """
    Get overall totals and margin metrics for a forwarding job.
    
    Returns a dictionary with:
    {
        'quoted_revenue': total,
        'quoted_cost': total,
        'quoted_margin': margin,
        'quoted_margin_percent': percent,
        'working_revenue': total,
        'working_cost': total,
        'working_margin': margin,
        'working_margin_percent': percent,
        'invoiced_revenue': total,
        'invoiced_cost': total,
        'invoiced_margin': margin,
        'invoiced_margin_percent': percent
    }
    """
    try:
        doc = frappe.get_doc('Forwarding Job', job_name)
    except frappe.DoesNotExistError:
        return {}
    
    quoted_revenue = flt(doc.total_quoted_revenue or 0)
    quoted_cost = flt(doc.total_quoted_cost or 0)
    working_revenue = flt(doc.total_working_revenue or 0)
    working_cost = flt(doc.total_working_cost or 0)
    
    # Get invoiced totals
    invoiced_revenue = 0
    invoiced_cost = 0
    
    sales_invoices = frappe.get_all(
        'Sales Invoice',
        filters={'forwarding_job_reference': job_name, 'docstatus': 1},
        fields=['total']
    )
    invoiced_revenue = sum([flt(si.get('total', 0)) for si in sales_invoices])
    
    purchase_invoices = frappe.get_all(
        'Purchase Invoice',
        filters={'forwarding_job_reference': job_name, 'docstatus': 1},
        fields=['total']
    )
    invoiced_cost = sum([flt(pi.get('total', 0)) for pi in purchase_invoices])
    
    quoted_margin = quoted_revenue - quoted_cost
    working_margin = working_revenue - working_cost
    invoiced_margin = invoiced_revenue - invoiced_cost
    
    quoted_margin_percent = (quoted_margin / quoted_revenue * 100) if quoted_revenue > 0 else 0
    working_margin_percent = (working_margin / working_revenue * 100) if working_revenue > 0 else 0
    invoiced_margin_percent = (invoiced_margin / invoiced_revenue * 100) if invoiced_revenue > 0 else 0
    
    return {
        'quoted_revenue': quoted_revenue,
        'quoted_cost': quoted_cost,
        'quoted_margin': quoted_margin,
        'quoted_margin_percent': quoted_margin_percent,
        'working_revenue': working_revenue,
        'working_cost': working_cost,
        'working_margin': working_margin,
        'working_margin_percent': working_margin_percent,
        'invoiced_revenue': invoiced_revenue,
        'invoiced_cost': invoiced_cost,
        'invoiced_margin': invoiced_margin,
        'invoiced_margin_percent': invoiced_margin_percent
    }


@frappe.whitelist()
def get_charge_details_for_cost_sheet(job_name):
    """
    Get organized charge details formatted specifically for cost sheet templates.
    
    Returns:
    {
        'charges': [
            {
                'charge': name,
                'quoted_revenue': amount,
                'quoted_cost': amount,
                'working_revenue': amount,
                'working_cost': amount,
                'invoiced_revenue': amount,
                'invoiced_cost': amount
            }
        ],
        'totals': {
            'quoted_revenue': total,
            'quoted_cost': total,
            'working_revenue': total,
            'working_cost': total,
            'invoiced_revenue': total,
            'invoiced_cost': total,
            'invoiced_margin': margin
        }
    }
    """
    charges_summary = get_all_charges_summary(job_name)
    totals = get_job_totals_summary(job_name)
    
    charges_list = []
    for charge_name, amounts in charges_summary.items():
        charges_list.append({
            'charge': charge_name,
            'quoted_revenue': amounts['quoted_revenue'],
            'quoted_cost': amounts['quoted_cost'],
            'working_revenue': amounts['working_revenue'],
            'working_cost': amounts['working_cost'],
            'invoiced_revenue': amounts['invoiced_revenue'],
            'invoiced_cost': amounts['invoiced_cost']
        })
    
    return {
        'charges': sorted(charges_list, key=lambda x: x['charge']),
        'totals': {
            'quoted_revenue': totals['quoted_revenue'],
            'quoted_cost': totals['quoted_cost'],
            'working_revenue': totals['working_revenue'],
            'working_cost': totals['working_cost'],
            'invoiced_revenue': totals['invoiced_revenue'],
            'invoiced_cost': totals['invoiced_cost'],
            'invoiced_margin': totals['invoiced_margin']
        }
    }


@frappe.whitelist()
def get_party_details_for_cost_sheet(job_name):
    """
    Get organized party (customer/supplier) details formatted for cost sheet templates.
    
    Returns:
    {
        'customers': [
            {
                'party': name,
                'quoted_revenue': amount,
                'quoted_cost': amount,
                'working_revenue': amount,
                'working_cost': amount,
                'invoiced_revenue': amount,
                'invoiced_cost': amount
            }
        ],
        'suppliers': [
            {
                'party': name,
                'quoted_revenue': amount,
                'quoted_cost': amount,
                'working_revenue': amount,
                'working_cost': amount,
                'invoiced_revenue': amount,
                'invoiced_cost': amount
            }
        ],
        'totals': {
            'quoted_revenue': total,
            'quoted_cost': total,
            'working_revenue': total,
            'working_cost': total,
            'invoiced_revenue': total,
            'invoiced_cost': total
        }
    }
    """
    parties_summary = get_all_parties_summary(job_name)
    
    customers = []
    suppliers = []
    
    for party_name, amounts in parties_summary.items():
        party_data = {
            'party': party_name,
            'quoted_revenue': amounts['quoted_revenue'],
            'quoted_cost': amounts['quoted_cost'],
            'working_revenue': amounts['working_revenue'],
            'working_cost': amounts['working_cost'],
            'invoiced_revenue': amounts['invoiced_revenue'],
            'invoiced_cost': amounts['invoiced_cost']
        }
        
        if amounts['party_type'] == 'Customer':
            customers.append(party_data)
        else:
            suppliers.append(party_data)
    
    totals = get_job_totals_summary(job_name)
    
    return {
        'customers': sorted(customers, key=lambda x: x['party']),
        'suppliers': sorted(suppliers, key=lambda x: x['party']),
        'totals': {
            'quoted_revenue': totals['quoted_revenue'],
            'quoted_cost': totals['quoted_cost'],
            'working_revenue': totals['working_revenue'],
            'working_cost': totals['working_cost'],
            'invoiced_revenue': totals['invoiced_revenue'],
            'invoiced_cost': totals['invoiced_cost']
        }
    }
