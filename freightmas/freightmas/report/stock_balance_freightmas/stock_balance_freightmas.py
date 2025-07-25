# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 180
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 240
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Opening Qty"),
            "fieldname": "opening_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("In Qty"),
            "fieldname": "in_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Out Qty"),
            "fieldname": "out_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Balance Qty"),
            "fieldname": "balance_qty",
            "fieldtype": "Float",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    stock_ledger_entries = get_stock_ledger_entries(filters, conditions)
    iwb_map = get_item_warehouse_map(stock_ledger_entries, filters)
    
    data = []
    for key, value in iwb_map.items():
        item_code, warehouse = key
        
        # Skip items with zero balance if not requested
        if not filters.get("include_zero_stock_items") and not value.get("balance_qty"):
            continue
            
        data.append({
            "item_code": item_code,
            "warehouse": warehouse,
            "stock_uom": value.get("stock_uom"),
            "opening_qty": flt(value.get("opening_qty"), 3),
            "in_qty": flt(value.get("in_qty"), 3),
            "out_qty": flt(value.get("out_qty"), 3),
            "balance_qty": flt(value.get("balance_qty"), 3)
        })
    
    return data

def get_conditions(filters):
    conditions = ""
    
    if filters.get("company"):
        conditions += " AND sle.company = %(company)s"
    if filters.get("warehouse"):
        conditions += " AND sle.warehouse = %(warehouse)s"
    if filters.get("item_code"):
        conditions += " AND sle.item_code = %(item_code)s"
    if filters.get("item_group"):
        conditions += " AND i.item_group = %(item_group)s"
    if filters.get("warehouse_type"):
        conditions += " AND w.warehouse_type = %(warehouse_type)s"
    
    return conditions

def get_stock_ledger_entries(filters, conditions):
    return frappe.db.sql("""
        SELECT
            sle.item_code,
            sle.warehouse,
            sle.posting_date,
            sle.actual_qty,
            i.stock_uom
        FROM
            `tabStock Ledger Entry` sle
        INNER JOIN
            `tabItem` i ON sle.item_code = i.name
        INNER JOIN
            `tabWarehouse` w ON sle.warehouse = w.name
        WHERE
            sle.docstatus < 2
            AND sle.posting_date <= %(to_date)s
            {conditions}
        ORDER BY
            sle.item_code, sle.warehouse, sle.posting_date
    """.format(conditions=conditions), filters, as_dict=1)

def get_item_warehouse_map(sle, filters):
    iwb_map = {}
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    
    for d in sle:
        key = (d.item_code, d.warehouse)
        if key not in iwb_map:
            iwb_map[key] = {
                "opening_qty": 0.0,
                "in_qty": 0.0,
                "out_qty": 0.0,
                "balance_qty": 0.0,
                "stock_uom": d.stock_uom
            }
        
        qty_dict = iwb_map[key]
        
        if d.posting_date < from_date:
            qty_dict["opening_qty"] += flt(d.actual_qty)
        elif d.posting_date >= from_date and d.posting_date <= to_date:
            if flt(d.actual_qty) > 0:
                qty_dict["in_qty"] += flt(d.actual_qty)
            else:
                qty_dict["out_qty"] += abs(flt(d.actual_qty))
        
        qty_dict["balance_qty"] += flt(d.actual_qty)
    
    return iwb_map