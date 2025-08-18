# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe


class TripBulkSalesInvoice(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        sub_total = 0
        vat = 0
        grand_total = 0
        total_quantity = 0

        for row in self.trip_bulk_sales_invoice_item:
            sub_total += float(row.amount or 0)
            total_quantity += float(row.qty or 0)

        vat = 0  # Set as needed
        grand_total = sub_total + vat

        self.sub_total = sub_total
        self.vat = vat
        self.grand_total = grand_total
        self.total_quantity = total_quantity
