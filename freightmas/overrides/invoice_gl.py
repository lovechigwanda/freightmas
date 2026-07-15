# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Invoice class overrides for revenue recognition GL visibility.

ERPNext merges GL lines that share the same merge key (account, cost center,
voucher_detail_no, ...) — both inside get_gl_entries and again in
general_ledger.make_gl_entries — so a job-linked invoice whose items all route
to the same WIP account shows ONE consolidated WIP line in the ledger. These
overrides flag each item's WIP line with core's `_skip_merge` escape hatch
right after the item lines are built (before the internal merge), so each
charge posts its own GL line, with the charge name stamped into its remarks.
"""

from frappe.utils import flt

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


def _get_job_wip_context(invoice, account_getter):
    """
    Return (wip_account, job_name, customer_reference) if the invoice is
    job-linked and RR is enabled, else (None, None, None).
    """
    import frappe
    from freightmas.utils.revenue_recognition import (
        get_recognition_job_reference,
        is_revenue_recognition_enabled,
    )

    job_doctype, job_name, _, _ = get_recognition_job_reference(invoice)
    if not job_name or not is_revenue_recognition_enabled():
        return None, None, None
    customer_ref = frappe.db.get_value(job_doctype, job_name, "customer_reference")
    return account_getter(), job_name, customer_ref


def _keep_wip_lines_separate(invoice, item_lines, wip_account, invoice_account_field,
                             side, job_name, customer_ref):
    """
    Flag job-linked WIP item GL lines `_skip_merge` and stamp per-charge remarks
    carrying the charge name, job ID and customer reference.

    Args:
        invoice: the Sales/Purchase Invoice document
        item_lines: the GL map entries appended by make_item_gl_entries
        wip_account: the WIP account items were routed to
        invoice_account_field: 'income_account' or 'expense_account'
        side: 'credit' (Sales Invoice) or 'debit' (Purchase Invoice)
        job_name: the linked job ID
        customer_ref: the job's customer reference
    """
    wip_lines = [
        entry for entry in item_lines
        if entry.get("account") == wip_account and flt(entry.get(side)) > 0
    ]
    if not wip_lines:
        return

    for entry in wip_lines:
        entry["_skip_merge"] = 1

    # One item line is appended per item in item order, so the n-th WIP line
    # belongs to the n-th WIP-routed item. Only stamp remarks when the counts
    # line up (defensive against asset/deferred items producing extra lines).
    wip_items = [
        item for item in invoice.items
        if item.get(invoice_account_field) == wip_account
    ]
    if len(wip_items) != len(wip_lines):
        return

    # Job + reference lead so consolidated GL views (which keep the first
    # row's remark for the whole group) still read correctly
    for item, entry in zip(wip_items, wip_lines):
        charge = item.item_name or item.item_code
        entry["remarks"] = f"{job_name}, Ref: {customer_ref or 'N/A'} - {charge}"


class FreightMasSalesInvoice(SalesInvoice):
    def validate(self):
        # ERPNext auto-learns each item's income account into its Item Default
        # (set_default_income_account_for_item, inside SellingController.validate,
        # which runs BEFORE our doc_event hook re-forces WIP). On re-save/submit
        # the items still carry WIP from the previous cycle, so ERPNext would
        # learn the WIP account as the item's default. Reset WIP back to empty
        # first: ERPNext re-resolves the natural account, learning never sees
        # WIP, and our validate hook afterwards snapshots and re-forces WIP.
        from freightmas.utils.revenue_recognition import (
            get_recognition_job_reference,
            get_recognition_settings,
            is_revenue_recognition_enabled,
        )

        _, job_name, _, _ = get_recognition_job_reference(self)
        if job_name and is_revenue_recognition_enabled():
            wip_account = get_recognition_settings().get("wip_revenue_account")
            if wip_account:
                for item in self.items:
                    if item.income_account == wip_account:
                        item.income_account = None

        super().validate()

    def make_item_gl_entries(self, gl_entries):
        start = len(gl_entries)
        super().make_item_gl_entries(gl_entries)

        from freightmas.utils.revenue_recognition import get_wip_revenue_account
        wip_account, job_name, customer_ref = _get_job_wip_context(self, get_wip_revenue_account)
        if wip_account:
            _keep_wip_lines_separate(
                self, gl_entries[start:], wip_account, "income_account", "credit",
                job_name, customer_ref
            )


class FreightMasPurchaseInvoice(PurchaseInvoice):
    def make_item_gl_entries(self, gl_entries):
        start = len(gl_entries)
        super().make_item_gl_entries(gl_entries)

        from freightmas.utils.revenue_recognition import get_wip_cost_account
        wip_account, job_name, customer_ref = _get_job_wip_context(self, get_wip_cost_account)
        if wip_account:
            _keep_wip_lines_separate(
                self, gl_entries[start:], wip_account, "expense_account", "debit",
                job_name, customer_ref
            )
