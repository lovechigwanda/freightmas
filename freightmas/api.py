import frappe
from erpnext.stock.utils import get_incoming_rate

@frappe.whitelist()
def get_fuel_rate(item_code, warehouse, posting_date=None):
    if not posting_date:
        posting_date = frappe.utils.today()

    args = {
        "item_code": item_code,
        "warehouse": warehouse,
        "posting_date": posting_date,
        "qty": 1,
        "allow_zero_valuation": 1
    }

    rate = get_incoming_rate(args)
    return rate or 0

