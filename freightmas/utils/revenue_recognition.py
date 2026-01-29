# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Revenue Recognition Utility Module

This module provides event-based revenue recognition for FreightMas services.
Revenue is recognized when jobs are completed (submitted), not when invoices are raised.

Accounting Flow:
1. On Sales Invoice submission (linked to a job):
   - Dr Accounts Receivable
   - Cr Unearned Revenue

2. On Job submission (completion):
   - Dr Unearned Revenue
   - Cr Service Revenue (Forwarding/Trucking/Clearing/Road Freight)

Supports:
- Multiple invoices per job (one JE line per invoice for traceability)
- Late invoices (auto-recognition if job already completed)
- Invoice amendments (auto-adjustment with correcting JE)
- Multi-currency with base currency conversion
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_link_to_form


def get_recognition_settings():
    """
    Fetch revenue recognition settings from FreightMas Settings.
    
    Returns:
        dict: Settings including enable flag, unearned revenue account,
              and service-specific revenue accounts
    """
    settings = frappe.get_single("FreightMas Settings")
    return {
        "enabled": settings.enable_revenue_recognition,
        "unearned_revenue_account": settings.unearned_revenue_account,
        "forwarding_revenue_account": settings.forwarding_revenue_account,
        "trucking_revenue_account": settings.trucking_revenue_account,
        "clearing_revenue_account": settings.clearing_revenue_account,
        "road_freight_revenue_account": settings.road_freight_revenue_account,
    }


@frappe.whitelist()
def is_revenue_recognition_enabled():
    """Check if revenue recognition is enabled in settings."""
    settings = get_recognition_settings()
    return settings.get("enabled", False)


def get_unearned_revenue_account():
    """Get the configured Unearned Revenue account."""
    settings = get_recognition_settings()
    account = settings.get("unearned_revenue_account")
    if not account:
        frappe.throw(
            _("Unearned Revenue Account not configured in FreightMas Settings")
        )
    return account


def get_service_revenue_account(service_type):
    """
    Get the revenue account for a specific service type.
    
    Args:
        service_type: One of 'forwarding', 'trucking', 'clearing', 'road_freight'
    
    Returns:
        str: Account name
    """
    settings = get_recognition_settings()
    account_key = f"{service_type}_revenue_account"
    account = settings.get(account_key)
    if not account:
        frappe.throw(
            _("{0} Revenue Account not configured in FreightMas Settings").format(
                service_type.replace("_", " ").title()
            )
        )
    return account


def get_linked_sales_invoices(job_doctype, job_name, only_submitted=True):
    """
    Get all Sales Invoices linked to a job.
    
    Args:
        job_doctype: The job doctype name (e.g., 'Forwarding Job')
        job_name: The job document name
        only_submitted: If True, only return submitted (docstatus=1) invoices
    
    Returns:
        list: List of Sales Invoice documents
    """
    # Map job doctype to the custom field used for linking
    link_field_map = {
        "Forwarding Job": "forwarding_job_reference",
        "Clearing Job": "clearing_job_reference",
        "Trip": "trip_reference",
        "Road Freight Job": "road_freight_job_reference",
    }
    
    link_field = link_field_map.get(job_doctype)
    if not link_field:
        frappe.throw(_("Unsupported job doctype: {0}").format(job_doctype))
    
    filters = {link_field: job_name}
    if only_submitted:
        filters["docstatus"] = 1
    
    invoice_names = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        pluck="name"
    )
    
    return [frappe.get_doc("Sales Invoice", name) for name in invoice_names]


def create_recognition_journal_entry(job_doc, invoices, recognition_date, service_type):
    """
    Create a Journal Entry to recognize revenue for completed job.
    
    Creates one debit/credit pair per invoice for full traceability.
    Uses company base currency with proper exchange rate conversion.
    
    Args:
        job_doc: The job document (Forwarding Job, Trip, etc.)
        invoices: List of Sales Invoice documents to recognize
        recognition_date: Date for revenue recognition
        service_type: One of 'forwarding', 'trucking', 'clearing', 'road_freight'
    
    Returns:
        str: Name of the created Journal Entry
    """
    if not invoices:
        frappe.throw(_("No invoices found for revenue recognition"))
    
    unearned_account = get_unearned_revenue_account()
    revenue_account = get_service_revenue_account(service_type)
    
    company = job_doc.company
    base_currency = frappe.get_cached_value("Company", company, "default_currency")
    
    accounts = []
    total_recognized = 0
    
    for invoice in invoices:
        # Calculate base amount using invoice's conversion rate
        invoice_total = flt(invoice.grand_total)
        conversion_rate = flt(invoice.conversion_rate) or 1
        base_amount = flt(invoice_total * conversion_rate)
        
        total_recognized += base_amount
        
        # Get cost center from first invoice item if available
        cost_center = None
        if invoice.items:
            cost_center = invoice.items[0].cost_center
        
        remark = _("Revenue recognition for {0} - Invoice {1}").format(
            job_doc.name, invoice.name
        )
        
        # Debit Unearned Revenue (reduce liability)
        accounts.append({
            "account": unearned_account,
            "debit_in_account_currency": base_amount,
            "cost_center": cost_center,
            "user_remark": remark,
        })
        
        # Credit Revenue Account (recognize income)
        accounts.append({
            "account": revenue_account,
            "credit_in_account_currency": base_amount,
            "cost_center": cost_center,
            "user_remark": remark,
        })
    
    if not accounts:
        frappe.throw(_("No accounting entries to create for revenue recognition"))
    
    # Create Journal Entry
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": recognition_date,
        "company": company,
        "user_remark": _("Revenue Recognition for {0} {1}").format(
            job_doc.doctype, job_doc.name
        ),
        "accounts": accounts,
    })
    
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    
    frappe.msgprint(
        _("Revenue Recognition Journal Entry {0} created for {1}").format(
            get_link_to_form("Journal Entry", je.name),
            frappe.format_value(total_recognized, {"fieldtype": "Currency"})
        ),
        alert=True
    )
    
    return je.name, total_recognized


def create_single_invoice_recognition_je(job_doc, invoice, recognition_date, service_type):
    """
    Create a Journal Entry for a single invoice (used for late invoices).
    
    Args:
        job_doc: The job document
        invoice: Single Sales Invoice document
        recognition_date: Date for revenue recognition
        service_type: Service type for revenue account selection
    
    Returns:
        str: Name of the created Journal Entry
    """
    return create_recognition_journal_entry(
        job_doc, [invoice], recognition_date, service_type
    )


def create_reversal_journal_entry(original_je_name, reversal_date=None, reason=None):
    """
    Create a reversal Journal Entry for an existing recognition entry.
    
    Args:
        original_je_name: Name of the Journal Entry to reverse
        reversal_date: Date for the reversal (defaults to today)
        reason: Optional reason for reversal
    
    Returns:
        str: Name of the reversal Journal Entry
    """
    if not reversal_date:
        reversal_date = nowdate()
    
    original_je = frappe.get_doc("Journal Entry", original_je_name)
    
    if original_je.docstatus != 1:
        frappe.throw(
            _("Cannot reverse Journal Entry {0} - it is not submitted").format(
                original_je_name
            )
        )
    
    # Create reversal by swapping debits and credits
    reversal_accounts = []
    for account in original_je.accounts:
        reversal_accounts.append({
            "account": account.account,
            "debit_in_account_currency": flt(account.credit_in_account_currency),
            "credit_in_account_currency": flt(account.debit_in_account_currency),
            "cost_center": account.cost_center,
            "user_remark": _("Reversal: {0}").format(account.user_remark or ""),
        })
    
    reversal_remark = _("Reversal of {0}").format(original_je_name)
    if reason:
        reversal_remark += f" - {reason}"
    
    reversal_je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": reversal_date,
        "company": original_je.company,
        "user_remark": reversal_remark,
        "accounts": reversal_accounts,
    })
    
    reversal_je.flags.ignore_permissions = True
    reversal_je.insert()
    reversal_je.submit()
    
    frappe.msgprint(
        _("Reversal Journal Entry {0} created").format(
            get_link_to_form("Journal Entry", reversal_je.name)
        ),
        alert=True
    )
    
    return reversal_je.name


def validate_invoice_income_account(invoice_doc):
    """
    Validate that a forwarding-linked invoice uses the correct Unearned Revenue account.
    Called before Sales Invoice submission.
    
    Args:
        invoice_doc: The Sales Invoice document
    """
    if not is_revenue_recognition_enabled():
        return
    
    # Check if this is a forwarding invoice
    is_forwarding = getattr(invoice_doc, "is_forwarding_invoice", 0)
    job_reference = getattr(invoice_doc, "forwarding_job_reference", None)
    
    if not is_forwarding or not job_reference:
        return
    
    unearned_account = get_unearned_revenue_account()
    
    for item in invoice_doc.items:
        if item.income_account != unearned_account:
            frappe.throw(
                _("Row {0}: Income account must be {1} for Forwarding Job invoices. "
                  "Found: {2}").format(
                    item.idx, unearned_account, item.income_account
                )
            )


def recognize_revenue_for_job(job_doc, service_type):
    """
    Main function to recognize revenue when a job is submitted.
    
    Args:
        job_doc: The job document being submitted
        service_type: One of 'forwarding', 'trucking', 'clearing', 'road_freight'
    """
    if not is_revenue_recognition_enabled():
        return
    
    if job_doc.revenue_recognised:
        frappe.throw(
            _("Revenue has already been recognised for this job. "
              "Journal Entry: {0}").format(job_doc.revenue_recognition_journal_entry)
        )
    
    if not job_doc.revenue_recognised_on:
        frappe.throw(
            _("Please set the Revenue Recognition Date before submitting the job")
        )
    
    # Get all submitted sales invoices linked to this job
    invoices = get_linked_sales_invoices(job_doc.doctype, job_doc.name)
    
    if not invoices:
        # No invoices yet - job can be submitted, revenue will be recognized
        # when invoices are raised later
        frappe.msgprint(
            _("No invoices found. Revenue will be recognized when invoices are submitted."),
            alert=True
        )
        job_doc.revenue_recognised = 1
        job_doc.total_recognised_revenue = 0
        return
    
    # Create recognition Journal Entry
    je_name, total_recognized = create_recognition_journal_entry(
        job_doc,
        invoices,
        job_doc.revenue_recognised_on,
        service_type
    )
    
    # Update job with recognition details
    job_doc.revenue_recognised = 1
    job_doc.revenue_recognition_journal_entry = je_name
    job_doc.total_recognised_revenue = total_recognized


def reverse_revenue_recognition(job_doc):
    """
    Reverse revenue recognition when a job is cancelled.
    
    Args:
        job_doc: The job document being cancelled
    """
    if not job_doc.revenue_recognised:
        return
    
    if job_doc.revenue_recognition_journal_entry:
        # Cancel the recognition Journal Entry
        je = frappe.get_doc("Journal Entry", job_doc.revenue_recognition_journal_entry)
        if je.docstatus == 1:
            je.flags.ignore_permissions = True
            je.cancel()
            frappe.msgprint(
                _("Revenue Recognition Journal Entry {0} cancelled").format(
                    job_doc.revenue_recognition_journal_entry
                ),
                alert=True
            )
    
    # Reset recognition fields
    job_doc.revenue_recognised = 0
    job_doc.revenue_recognition_journal_entry = None
    job_doc.total_recognised_revenue = 0


def handle_late_invoice_submission(invoice_doc, job_doctype, job_link_field, service_type):
    """
    Handle submission of an invoice after the linked job is already recognized.
    Creates an immediate recognition JE for this invoice.
    
    Args:
        invoice_doc: The Sales Invoice being submitted
        job_doctype: The job doctype (e.g., 'Forwarding Job')
        job_link_field: The custom field linking to the job
        service_type: Service type for revenue account
    """
    if not is_revenue_recognition_enabled():
        return
    
    job_reference = getattr(invoice_doc, job_link_field, None)
    if not job_reference:
        return
    
    job_doc = frappe.get_doc(job_doctype, job_reference)
    
    # Check if job already has revenue recognized
    if not job_doc.revenue_recognised or not job_doc.revenue_recognised_on:
        return
    
    # Create immediate recognition for this invoice
    je_name, amount = create_single_invoice_recognition_je(
        job_doc,
        invoice_doc,
        job_doc.revenue_recognised_on,
        service_type
    )
    
    # Update job's total recognized revenue
    job_doc.total_recognised_revenue = flt(job_doc.total_recognised_revenue) + amount
    job_doc.flags.ignore_validate_update_after_submit = True
    job_doc.save()
    
    frappe.msgprint(
        _("Late invoice revenue recognized immediately. Journal Entry: {0}").format(
            get_link_to_form("Journal Entry", je_name)
        ),
        alert=True
    )


def handle_invoice_cancellation(invoice_doc, job_doctype, job_link_field, service_type):
    """
    Handle cancellation of an invoice linked to a recognized job.
    Creates a reversal JE for the recognized portion.
    
    Args:
        invoice_doc: The Sales Invoice being cancelled
        job_doctype: The job doctype (e.g., 'Forwarding Job')
        job_link_field: The custom field linking to the job
        service_type: Service type for lookup
    """
    if not is_revenue_recognition_enabled():
        return
    
    job_reference = getattr(invoice_doc, job_link_field, None)
    if not job_reference:
        return
    
    job_doc = frappe.get_doc(job_doctype, job_reference)
    
    if not job_doc.revenue_recognised:
        return
    
    # Find recognition JE entries for this specific invoice
    je_name = job_doc.revenue_recognition_journal_entry
    if not je_name:
        return
    
    je = frappe.get_doc("Journal Entry", je_name)
    
    # Calculate amount to reverse for this invoice by checking user_remark
    invoice_amount = 0
    for account in je.accounts:
        if (account.user_remark and invoice_doc.name in account.user_remark and
            flt(account.credit_in_account_currency) > 0):
            invoice_amount = flt(account.credit_in_account_currency)
            break
    
    if invoice_amount > 0:
        # Create partial reversal for this invoice
        unearned_account = get_unearned_revenue_account()
        revenue_account = get_service_revenue_account(service_type)
        
        reversal_je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": nowdate(),
            "company": job_doc.company,
            "user_remark": _("Reversal for cancelled Invoice {0}").format(invoice_doc.name),
            "accounts": [
                {
                    "account": revenue_account,
                    "debit_in_account_currency": invoice_amount,
                    "user_remark": _("Reversal: Invoice {0} cancelled").format(invoice_doc.name),
                },
                {
                    "account": unearned_account,
                    "credit_in_account_currency": invoice_amount,
                    "user_remark": _("Reversal: Invoice {0} cancelled").format(invoice_doc.name),
                }
            ],
        })
        
        reversal_je.flags.ignore_permissions = True
        reversal_je.insert()
        reversal_je.submit()
        
        # Update job's total
        job_doc.total_recognised_revenue = flt(job_doc.total_recognised_revenue) - invoice_amount
        job_doc.flags.ignore_validate_update_after_submit = True
        job_doc.save()
        
        frappe.msgprint(
            _("Revenue reversal Journal Entry {0} created for cancelled invoice").format(
                get_link_to_form("Journal Entry", reversal_je.name)
            ),
            alert=True
        )


# Forwarding Job specific handlers
def on_forwarding_job_submit(doc, method=None):
    """Hook called when Forwarding Job is submitted."""
    recognize_revenue_for_job(doc, "forwarding")


def on_forwarding_job_cancel(doc, method=None):
    """Hook called when Forwarding Job is cancelled."""
    reverse_revenue_recognition(doc)


# Sales Invoice handlers
def on_sales_invoice_submit(doc, method=None):
    """Hook called when Sales Invoice is submitted."""
    # Check for Forwarding Job link
    if getattr(doc, "is_forwarding_invoice", 0) and \
       getattr(doc, "forwarding_job_reference", None):
        handle_late_invoice_submission(
            doc,
            "Forwarding Job",
            "forwarding_job_reference",
            "forwarding"
        )


def before_sales_invoice_submit(doc, method=None):
    """Hook called before Sales Invoice submission for validation."""
    validate_invoice_income_account(doc)


def on_sales_invoice_cancel_for_recognition(doc, method=None):
    """Hook called when Sales Invoice is cancelled - handle recognition reversal."""
    # Check for Forwarding Job link
    if getattr(doc, "is_forwarding_invoice", 0) and \
       getattr(doc, "forwarding_job_reference", None):
        handle_invoice_cancellation(
            doc,
            "Forwarding Job",
            "forwarding_job_reference",
            "forwarding"
        )
