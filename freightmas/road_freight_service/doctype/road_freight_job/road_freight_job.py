# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from frappe import _

class RoadFreightJob(Document):
    def validate(self):
        self.set_base_currency()
        self.calculate_totals()
        self.validate_customer_and_supplier()
        self.prevent_editing_invoiced_rows()

    def set_base_currency(self):
        if not self.base_currency and self.company:
            self.base_currency = frappe.db.get_value("Company", self.company, "default_currency")
        if not self.conversion_rate:
            self.conversion_rate = 1.0

    def calculate_totals(self):
        total_revenue = 0
        total_cost = 0

        for row in self.road_freight_charges:
            row.revenue_amount = flt(row.qty) * flt(row.sell_rate)
            row.cost_amount = flt(row.qty) * flt(row.buy_rate)
            total_revenue += flt(row.revenue_amount)
            total_cost += flt(row.cost_amount)

        total_profit = total_revenue - total_cost
        rate = flt(self.conversion_rate)

        self.total_estimated_revenue = total_revenue
        self.total_estimated_cost = total_cost
        self.total_estimated_profit = total_profit

        self.total_estimated_revenue_base = total_revenue * rate
        self.total_estimated_cost_base = total_cost * rate
        self.total_estimated_profit_base = total_profit * rate

    def validate_customer_and_supplier(self):
        for row in self.road_freight_charges:
            if row.sell_rate and not row.customer:
                frappe.throw(
                    _("Customer is required for row {0} because Sell Rate is entered.").format(row.idx),
                    title="Missing Customer"
                )
            if row.buy_rate and not row.supplier:
                frappe.throw(
                    _("Supplier is required for row {0} because Buy Rate is entered.").format(row.idx),
                    title="Missing Supplier"
                )

    def prevent_editing_invoiced_rows(self):
        for row in self.road_freight_charges:
            if not row.name or row.name.startswith("NEW-"):
                continue

            if not (row.sales_invoice_reference or row.purchase_invoice_reference):
                continue

            try:
                original = frappe.get_doc("Road Freight Charges", row.name)
            except frappe.DoesNotExistError:
                continue

            if row.sales_invoice_reference:
                for field in ["sell_rate", "customer", "qty"]:
                    if row.get(field) != original.get(field):
                        frappe.throw(
                            f"You cannot modify '{field}' on a charge already linked to Sales Invoice: {row.sales_invoice_reference}"
                        )

            if row.purchase_invoice_reference:
                for field in ["buy_rate", "supplier", "qty"]:
                    if row.get(field) != original.get(field):
                        frappe.throw(
                            f"You cannot modify '{field}' on a charge already linked to Purchase Invoice: {row.purchase_invoice_reference}"
                        )


# ========================================================
# SALES INVOICE CREATION
# ========================================================

@frappe.whitelist()
def create_sales_invoice_with_rows(docname, row_names):
    import json
    if isinstance(row_names, str):
        row_names = json.loads(row_names)

    job = frappe.get_doc("Road Freight Job", docname)
    selected_rows = [row for row in job.road_freight_charges if row.name in row_names]

    if not selected_rows:
        frappe.throw("No valid charges selected.")

    si = frappe.new_doc("Sales Invoice")
    si.customer = selected_rows[0].customer
    si.road_freight_job_reference = job.name
    si.is_road_freight_invoice = 1
    si.set_posting_time = 1
    si.posting_date = nowdate()
    si.currency = job.currency
    si.conversion_rate = job.conversion_rate or 1

    cargo_desc = job.cargo_description or "N/A"
    charge_list = ", ".join([row.charge for row in selected_rows])
    si.remarks = f"Road Freight Job {job.name} (Cargo: {cargo_desc}): {charge_list}"

    for row in selected_rows:
        si.append("items", {
            "item_code": row.charge,
            "description": row.description,
            "qty": row.qty or 1,
            "rate": row.sell_rate
        })

    si.insert()

    for row in job.road_freight_charges:
        if row.name in row_names:
            row.is_invoiced = 1
            row.sales_invoice_reference = si.name

    job.save()
    return si.name


# ========================================================
# PURCHASE INVOICE CREATION
# ========================================================

@frappe.whitelist()
def create_purchase_invoice_with_rows(docname, row_names):
    import json
    if isinstance(row_names, str):
        row_names = json.loads(row_names)

    job = frappe.get_doc("Road Freight Job", docname)
    selected_rows = [row for row in job.road_freight_charges if row.name in row_names]

    if not selected_rows:
        frappe.throw("No valid charges selected.")

    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = selected_rows[0].supplier
    pi.road_freight_job_reference = job.name
    pi.is_road_freight_invoice = 1
    pi.set_posting_time = 1
    pi.posting_date = nowdate()
    pi.currency = job.currency
    pi.conversion_rate = job.conversion_rate or 1

    cargo_desc = job.cargo_description or "N/A"
    charge_list = ", ".join([row.charge for row in selected_rows])
    pi.remarks = f"Road Freight Job {job.name} (Cargo: {cargo_desc}): {charge_list}"

    for row in selected_rows:
        pi.append("items", {
            "item_code": row.charge,
            "description": row.description,
            "qty": row.qty or 1,
            "rate": row.buy_rate
        })

    pi.insert()

    for row in job.road_freight_charges:
        if row.name in row_names:
            row.is_purchased = 1
            row.purchase_invoice_reference = pi.name

    job.save()
    return pi.name
