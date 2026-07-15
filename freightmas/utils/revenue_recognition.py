# Copyright (c) 2026, FreightMas and contributors
# For license information, please see license.txt

"""
Revenue Recognition Utility Module

This module provides event-based revenue recognition for FreightMas services.
Revenue is recognized when jobs are completed (submitted), not when invoices are raised.

Accounting Flow:
1. On Sales Invoice validate (linked to a job):
   - Each item's natural income account (Item Default -> Item Group -> Brand ->
     Company default, or user-chosen) is snapshotted into actual_income_account,
     then the item is routed to WIP Revenue.
2. On Sales Invoice submission:
   - Dr Accounts Receivable
   - Cr WIP Revenue (per item, net amount)

3. On Job submission (completion):
   - Dr WIP Revenue (net total per invoice)
   - Cr each item's snapshotted income account
     (fallback: the service-level revenue account from FreightMas Settings)

Purchase Invoices mirror this with actual_expense_account / WIP Cost.

Supports:
- Multiple invoices per job (JE lines carry the invoice name for traceability)
- Late invoices (auto-recognition if job already completed)
- Invoice amendments (auto-adjustment with correcting JE)
- Multi-currency with base currency conversion
- Border Clearing duty pass-through rows (settle at invoice time, never in WIP)
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_link_to_form

# Custom field on Sales/Purchase Invoice linking each job doctype to the invoice
JOB_LINK_FIELD_MAP = {
    "Forwarding Job": "forwarding_job_reference",
    "Clearing Job": "clearing_job_reference",
    "Trip": "trip_reference",
    "Road Freight Job": "road_freight_job_reference",
    "Border Clearing Job": "border_clearing_job_reference",
}

# Job types wired into the recognition engine: doctype -> (link field, service type).
# Trip / Road Freight Job are excluded: their controllers never call
# recognize_*_for_job, so forcing their invoices into WIP would strand balances.
RECOGNITION_JOB_TYPES = {
    "Forwarding Job": ("forwarding_job_reference", "forwarding"),
    "Clearing Job": ("clearing_job_reference", "clearing"),
    "Border Clearing Job": ("border_clearing_job_reference", "border_clearing"),
}


def get_recognition_job_reference(invoice_doc):
    """
    Find the first recognition-wired job reference set on an invoice.

    Returns:
        tuple: (job_doctype, job_name, link_field, service_type),
               or (None, None, None, None) if the invoice is not job-linked
    """
    for job_doctype, (link_field, service_type) in RECOGNITION_JOB_TYPES.items():
        job_name = invoice_doc.get(link_field)
        if job_name:
            return job_doctype, job_name, link_field, service_type
    return None, None, None, None


def get_recognition_settings():
    """
    Fetch revenue/cost recognition settings from FreightMas Settings.
    
    Returns:
        dict: Settings including enable flag, WIP revenue account,
              WIP cost account, and service-specific accounts
    """
    settings = frappe.get_single("FreightMas Settings")
    return {
        "enabled": settings.enable_revenue_recognition,
        # Revenue accounts
        "wip_revenue_account": settings.wip_revenue_account,
        "forwarding_revenue_account": settings.forwarding_revenue_account,
        "trucking_revenue_account": settings.trucking_revenue_account,
        "clearing_revenue_account": settings.clearing_revenue_account,
        "road_freight_revenue_account": settings.road_freight_revenue_account,
        "border_clearing_revenue_account": settings.border_clearing_revenue_account,
        # Cost accounts
        "wip_cost_account": settings.wip_cost_account,
        "forwarding_cost_account": settings.forwarding_cost_account,
        "trucking_cost_account": settings.trucking_cost_account,
        "clearing_cost_account": settings.clearing_cost_account,
        "road_freight_cost_account": settings.road_freight_cost_account,
        "border_clearing_cost_account": settings.border_clearing_cost_account,
    }


@frappe.whitelist()
def is_revenue_recognition_enabled():
    """Check if revenue recognition is enabled in settings."""
    settings = get_recognition_settings()
    return settings.get("enabled", False)


@frappe.whitelist()
def get_earliest_invoice_date(job_doctype, job_name):
    """
    Get the earliest invoice date for a job.
    Used by client-side to validate RR date selection.
    
    Returns:
        dict with earliest_date and invoice_count
    """
    invoices = get_linked_sales_invoices(job_doctype, job_name)
    
    if not invoices:
        return {
            "earliest_date": None,
            "invoice_count": 0
        }
    
    from frappe.utils import getdate
    earliest_date = min(getdate(inv.posting_date) for inv in invoices)
    
    return {
        "earliest_date": str(earliest_date),
        "invoice_count": len(invoices)
    }


def get_wip_revenue_account():
    """Get the configured WIP Revenue account."""
    settings = get_recognition_settings()
    account = settings.get("wip_revenue_account")
    if not account:
        frappe.throw(
            _("WIP Revenue Account not configured in FreightMas Settings")
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


def get_wip_cost_account():
    """Get the configured WIP Cost account."""
    settings = get_recognition_settings()
    account = settings.get("wip_cost_account")
    if not account:
        frappe.throw(
            _("WIP Cost Account not configured in FreightMas Settings")
        )
    return account


def get_service_cost_account(service_type):
    """
    Get the cost account for a specific service type.
    
    Args:
        service_type: One of 'forwarding', 'trucking', 'clearing', 'road_freight'
    
    Returns:
        str: Account name
    """
    settings = get_recognition_settings()
    account_key = f"{service_type}_cost_account"
    account = settings.get(account_key)
    if not account:
        frappe.throw(
            _("{0} Cost Account not configured in FreightMas Settings").format(
                service_type.replace("_", " ").title()
            )
        )
    return account


def get_duty_pass_through_account():
    """Get the duty pass-through account (Border Clearing), or None if unset."""
    return frappe.db.get_single_value("FreightMas Settings", "duty_pass_through_account")


def resolve_item_default_account(item_code, company, account_fieldname):
    """
    Resolve the account explicitly configured for an item:
    Item Default -> Item Group default -> Brand default.

    Deliberately does NOT consult the Company default income/expense account —
    that is only a last resort in the snapshot chain, after the per-service
    account from FreightMas Settings.

    Args:
        item_code: The Item code
        company: The company to resolve defaults for
        account_fieldname: 'income_account' or 'expense_account'

    Returns:
        str or None: Account name, or None if no explicit default exists
    """
    if not item_code:
        return None

    from erpnext.stock.doctype.item.item import get_item_defaults
    from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
    from erpnext.setup.doctype.brand.brand import get_brand_defaults

    for get_defaults in (get_item_defaults, get_item_group_defaults, get_brand_defaults):
        try:
            defaults = get_defaults(item_code, company)
        except Exception:
            defaults = None
        account = (defaults or {}).get(account_fieldname)
        if account:
            return account

    return None


def is_usable_account(account, company):
    """Check that an account exists, is a ledger (not group), enabled, and belongs to the company."""
    if not account:
        return False
    acc = frappe.db.get_value(
        "Account", account, ["company", "disabled", "is_group"], as_dict=True
    )
    return bool(acc) and not acc.disabled and not acc.is_group and acc.company == company


def remark_matches_invoice(remark, invoice_name):
    """
    Match a JE line to its invoice. Recognition remarks always end with
    '... Invoice {name}', so an end-anchored match avoids false positives
    between prefix-sharing names (e.g. INV-001 vs INV-0010).
    """
    return bool(remark) and remark.rstrip().endswith(" " + invoice_name)


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
    link_field = JOB_LINK_FIELD_MAP.get(job_doctype)
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


def get_linked_purchase_invoices(job_doctype, job_name, only_submitted=True):
    """
    Get all Purchase Invoices linked to a job.
    
    Args:
        job_doctype: The job doctype name (e.g., 'Forwarding Job')
        job_name: The job document name
        only_submitted: If True, only return submitted (docstatus=1) invoices
    
    Returns:
        list: List of Purchase Invoice documents
    """
    link_field = JOB_LINK_FIELD_MAP.get(job_doctype)
    if not link_field:
        frappe.throw(_("Unsupported job doctype: {0}").format(job_doctype))
    
    filters = {link_field: job_name}
    if only_submitted:
        filters["docstatus"] = 1
    
    invoice_names = frappe.get_all(
        "Purchase Invoice",
        filters=filters,
        pluck="name"
    )
    
    return [frappe.get_doc("Purchase Invoice", name) for name in invoice_names]


def build_recognition_lines(invoice, job_doc, wip_account, snapshot_field,
                            invoice_account_field, get_fallback_account, remark_builder, side):
    """
    Build per-charge recognition JE lines for one invoice.

    Only items that were actually parked in WIP participate (pass-through and
    historically non-WIP-routed items already posted their P&L at invoice time).
    Each charge gets its own mirror pair — WIP line + snapshotted-account line
    for its base net amount — so the JE literally reverses what the invoice
    put into WIP (net of taxes/discounts), charge by charge.

    Args:
        invoice: Sales/Purchase Invoice document
        job_doc: The job document (for company)
        wip_account: The WIP account items were routed to
        snapshot_field: 'actual_income_account' or 'actual_expense_account'
        invoice_account_field: 'income_account' or 'expense_account'
        get_fallback_account: callable returning the service-level account,
            invoked only when a line actually needs the fallback
        remark_builder: callable(charge_name) -> user_remark; the remark MUST
            end with the invoice name (remark_matches_invoice relies on it)
        side: 'revenue' (Cr item accounts / Dr WIP) or 'cost' (Dr / Cr)

    Returns:
        tuple: (lines, included_total)
    """
    company = job_doc.company
    item_side = "credit_in_account_currency" if side == "revenue" else "debit_in_account_currency"
    wip_side = "debit_in_account_currency" if side == "revenue" else "credit_in_account_currency"

    lines = []
    included_total = 0

    for item in invoice.items:
        if item.get(invoice_account_field) != wip_account:
            continue  # never entered WIP — nothing to recognise for this item
        amount = flt(item.base_net_amount)
        if amount <= 0:
            continue
        target = item.get(snapshot_field)
        if not is_usable_account(target, company):
            target = get_fallback_account()

        remark = remark_builder(item.item_name or item.item_code)
        lines.append({
            "account": wip_account,
            wip_side: amount,
            "cost_center": item.cost_center,
            "user_remark": remark,
        })
        lines.append({
            "account": target,
            item_side: amount,
            "cost_center": item.cost_center,
            "user_remark": remark,
        })
        included_total = flt(included_total + amount, 2)

    if included_total <= 0:
        return [], 0

    return lines, included_total


def create_recognition_journal_entry(job_doc, invoices, recognition_date, service_type):
    """
    Create a Journal Entry to recognize revenue for completed job.

    Per invoice: one Dr WIP Revenue line (net total) and one Cr line per
    snapshotted income account, so each charge lands on the account defined
    for its Item (fallback: the service revenue account from settings).

    Args:
        job_doc: The job document (Forwarding Job, Clearing Job, etc.)
        invoices: List of Sales Invoice documents to recognize
        recognition_date: Date for revenue recognition
        service_type: One of 'forwarding', 'clearing', 'border_clearing', ...

    Returns:
        tuple: (je_name, total_recognized), or (None, 0) if the invoices
               have nothing in WIP to recognize
    """
    if not invoices:
        frappe.throw(_("No invoices found for revenue recognition"))

    wip_revenue_account = get_wip_revenue_account()

    _fallback = []
    def get_fallback_account():
        if not _fallback:
            _fallback.append(get_service_revenue_account(service_type))
        return _fallback[0]

    company = job_doc.company

    accounts = []
    total_recognized = 0

    customer_ref = job_doc.get("customer_reference") or "N/A"

    for invoice in invoices:
        def remark_builder(charge, invoice_name=invoice.name):
            # job + ref lead so consolidated GL views read correctly;
            # must end with the invoice name — remark_matches_invoice relies on it
            return _("{0}, Ref: {1} - Revenue recognition of {2} - Invoice {3}").format(
                job_doc.name, customer_ref, charge, invoice_name
            )
        lines, included_total = build_recognition_lines(
            invoice, job_doc, wip_revenue_account,
            "actual_income_account", "income_account",
            get_fallback_account, remark_builder, "revenue"
        )
        accounts.extend(lines)
        total_recognized += included_total

    if not accounts:
        return None, 0

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


def create_cost_recognition_journal_entry(job_doc, invoices, recognition_date, service_type):
    """
    Create a Journal Entry to recognize cost for completed job.

    Per invoice: one Cr WIP Cost line (net total) and one Dr line per
    snapshotted expense account, so each charge lands on the account defined
    for its Item (fallback: the service cost account from settings).

    Accounting:
        Dr  each item's expense account
        Cr  WIP Cost (Asset)

    Args:
        job_doc: The job document (Forwarding Job, Clearing Job, etc.)
        invoices: List of Purchase Invoice documents to recognize
        recognition_date: Date for cost recognition
        service_type: One of 'forwarding', 'clearing', 'border_clearing', ...

    Returns:
        tuple: (je_name, total_recognized), or (None, 0) if the invoices
               have nothing in WIP to recognize
    """
    if not invoices:
        frappe.throw(_("No purchase invoices found for cost recognition"))

    wip_cost_account = get_wip_cost_account()

    _fallback = []
    def get_fallback_account():
        if not _fallback:
            _fallback.append(get_service_cost_account(service_type))
        return _fallback[0]

    company = job_doc.company

    accounts = []
    total_recognized = 0

    customer_ref = job_doc.get("customer_reference") or "N/A"

    for invoice in invoices:
        def remark_builder(charge, invoice_name=invoice.name):
            # job + ref lead so consolidated GL views read correctly;
            # must end with the invoice name — remark_matches_invoice relies on it
            return _("{0}, Ref: {1} - Cost recognition of {2} - Invoice {3}").format(
                job_doc.name, customer_ref, charge, invoice_name
            )
        lines, included_total = build_recognition_lines(
            invoice, job_doc, wip_cost_account,
            "actual_expense_account", "expense_account",
            get_fallback_account, remark_builder, "cost"
        )
        accounts.extend(lines)
        total_recognized += included_total

    if not accounts:
        return None, 0

    # Create Journal Entry
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": recognition_date,
        "company": company,
        "user_remark": _("Cost Recognition for {0} {1}").format(
            job_doc.doctype, job_doc.name
        ),
        "accounts": accounts,
    })
    
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    
    frappe.msgprint(
        _("Cost Recognition Journal Entry {0} created for {1}").format(
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
    Route job-linked Sales Invoice items through WIP Revenue, first snapshotting
    each item's natural income account into actual_income_account so job closure
    can post to it. Late recognition happens at on_submit.

    Called on Sales Invoice validate.

    Args:
        invoice_doc: The Sales Invoice document
    """
    if not is_revenue_recognition_enabled():
        return

    _, job_reference, _, service_type = get_recognition_job_reference(invoice_doc)
    if not job_reference:
        return

    wip_account = get_wip_revenue_account()
    pass_through_account = get_duty_pass_through_account()
    service_fallback = get_recognition_settings().get(f"{service_type}_revenue_account")
    company_default = frappe.get_cached_value(
        "Company", invoice_doc.company, "default_income_account"
    )

    for item in invoice_doc.items:
        # Duty pass-through rows settle at invoice time and never enter WIP
        if pass_through_account and item.income_account == pass_through_account:
            continue
        if (item.income_account
                and item.income_account != wip_account
                and item.income_account != company_default):
            # Explicit account: an item/group/brand default resolved by ERPNext,
            # or one picked on the line. The company default is excluded here —
            # ERPNext uses it as a catch-all, and unconfigured charges should
            # fall to the service account instead of generic Sales/COGS.
            item.actual_income_account = item.income_account
        elif not item.get("actual_income_account"):
            explicit = resolve_item_default_account(
                item.item_code, invoice_doc.company, "income_account"
            )
            if explicit == wip_account:
                # Item Default poisoned by ERPNext's account auto-learning
                # before the WIP guard existed — never snapshot WIP itself
                explicit = None
            item.actual_income_account = explicit or service_fallback or company_default
        item.income_account = wip_account


def validate_purchase_invoice_expense_account(invoice_doc):
    """
    Route job-linked Purchase Invoice items through WIP Cost, first snapshotting
    each item's natural expense account into actual_expense_account so job
    closure can post to it. Late recognition happens at on_submit.

    Called on Purchase Invoice validate.

    Args:
        invoice_doc: The Purchase Invoice document
    """
    if not is_revenue_recognition_enabled():
        return

    _, job_reference, _, service_type = get_recognition_job_reference(invoice_doc)
    if not job_reference:
        return

    wip_account = get_wip_cost_account()
    pass_through_account = get_duty_pass_through_account()
    service_fallback = get_recognition_settings().get(f"{service_type}_cost_account")
    company_default = frappe.get_cached_value(
        "Company", invoice_doc.company, "default_expense_account"
    )

    for item in invoice_doc.items:
        # Duty pass-through rows settle at invoice time and never enter WIP
        if pass_through_account and item.expense_account == pass_through_account:
            continue
        if (item.expense_account
                and item.expense_account != wip_account
                and item.expense_account != company_default):
            # Explicit account (see income mirror for the company-default rationale)
            item.actual_expense_account = item.expense_account
        elif not item.get("actual_expense_account"):
            explicit = resolve_item_default_account(
                item.item_code, invoice_doc.company, "expense_account"
            )
            if explicit == wip_account:
                # see income mirror — never snapshot WIP itself
                explicit = None
            item.actual_expense_account = explicit or service_fallback or company_default
        item.expense_account = wip_account


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
    # Filter out zero-amount invoices to prevent JE validation errors
    invoices = [inv for inv in invoices if flt(inv.grand_total) > 0]

    if not invoices:
        # No invoices yet - job can be submitted, revenue will be recognized
        # when invoices are raised later
        frappe.msgprint(
            _("No Sales Invoices with non-zero amounts linked to this job for revenue recognition."),
            alert=True
        )
        job_doc.revenue_recognised = 1
        job_doc.total_recognised_revenue = 0
        return
    
    # Validate RR date is not before earliest invoice date
    from frappe.utils import getdate
    rr_date = getdate(job_doc.revenue_recognised_on)
    earliest_invoice_date = min(getdate(inv.posting_date) for inv in invoices)
    
    if rr_date < earliest_invoice_date:
        frappe.throw(
            _("Revenue Recognition Date ({0}) cannot be earlier than the earliest "
              "invoice date ({1}). The WIP Revenue account would not have a "
              "balance to recognize from.").format(
                frappe.format_value(rr_date, {"fieldtype": "Date"}),
                frappe.format_value(earliest_invoice_date, {"fieldtype": "Date"})
            )
        )
    
    # Create recognition Journal Entry
    je_name, total_recognized = create_recognition_journal_entry(
        job_doc,
        invoices,
        job_doc.revenue_recognised_on,
        service_type
    )

    if not je_name:
        # Nothing parked in WIP (e.g. pass-through-only invoices) — never block closure
        frappe.msgprint(
            _("Linked Sales Invoices have no WIP Revenue balance to recognize."),
            alert=True
        )
        job_doc.revenue_recognised = 1
        job_doc.total_recognised_revenue = 0
        return

    # Update job with recognition details
    job_doc.revenue_recognised = 1
    job_doc.revenue_recognition_journal_entry = je_name
    job_doc.total_recognised_revenue = total_recognized


def reverse_revenue_recognition(job_doc):
    """
    Reverse revenue recognition when a job is cancelled.
    Cancels the main recognition JE and any late-invoice recognition JEs.

    Args:
        job_doc: The job document being cancelled
    """
    if not job_doc.revenue_recognised:
        return

    if job_doc.revenue_recognition_journal_entry:
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

    # Also cancel any late-invoice recognition JEs (submitted after job recognition)
    link_field = JOB_LINK_FIELD_MAP.get(job_doc.doctype)
    linked_si_names = frappe.get_all(
        "Sales Invoice",
        filters={link_field: job_doc.name},
        pluck="name"
    ) if link_field else []
    for si_name in linked_si_names:
        late_je_name = frappe.db.get_value("Sales Invoice", si_name, "recognition_journal_entry")
        if late_je_name:
            late_je = frappe.get_doc("Journal Entry", late_je_name)
            if late_je.docstatus == 1:
                late_je.flags.ignore_permissions = True
                late_je.cancel()
            frappe.db.set_value("Sales Invoice", si_name,
                "recognition_journal_entry", None, update_modified=False)

    # Reset recognition fields
    job_doc.revenue_recognised = 0
    job_doc.revenue_recognition_journal_entry = None
    job_doc.total_recognised_revenue = 0


def recognize_cost_for_job(job_doc, service_type):
    """
    Recognize cost when a job is submitted.
    Uses the same recognition date as revenue recognition.
    
    Args:
        job_doc: The job document being submitted
        service_type: One of 'forwarding', 'trucking', 'clearing', 'road_freight'
    """
    if not is_revenue_recognition_enabled():
        return
    
    if job_doc.cost_recognised:
        frappe.throw(
            _("Cost has already been recognised for this job. "
              "Journal Entry: {0}").format(job_doc.cost_recognition_journal_entry)
        )
    
    if not job_doc.revenue_recognised_on:
        frappe.throw(
            _("Please set the Revenue Recognition Date before submitting the job")
        )
    
    # Get all submitted purchase invoices linked to this job
    invoices = get_linked_purchase_invoices(job_doc.doctype, job_doc.name)
    # Filter out zero-amount invoices to prevent JE validation errors
    invoices = [inv for inv in invoices if flt(inv.grand_total) > 0]

    if not invoices:
        # No purchase invoices yet - mark as recognized with zero
        frappe.msgprint(
            _("No Purchase Invoices with non-zero amounts linked to this job for cost recognition."),
            alert=True
        )
        job_doc.cost_recognised = 1
        job_doc.total_recognised_cost = 0
        return
    
    # Validate recognition date is not before earliest purchase invoice date
    from frappe.utils import getdate
    rr_date = getdate(job_doc.revenue_recognised_on)
    earliest_invoice_date = min(getdate(inv.posting_date) for inv in invoices)
    
    if rr_date < earliest_invoice_date:
        frappe.throw(
            _("Recognition Date ({0}) cannot be earlier than the earliest "
              "purchase invoice date ({1}). The WIP Cost account would not have a "
              "balance to recognize from.").format(
                frappe.format_value(rr_date, {"fieldtype": "Date"}),
                frappe.format_value(earliest_invoice_date, {"fieldtype": "Date"})
            )
        )
    
    # Create cost recognition Journal Entry
    je_name, total_recognized = create_cost_recognition_journal_entry(
        job_doc,
        invoices,
        job_doc.revenue_recognised_on,
        service_type
    )

    if not je_name:
        # Nothing parked in WIP (e.g. pass-through-only invoices) — never block closure
        frappe.msgprint(
            _("Linked Purchase Invoices have no WIP Cost balance to recognize."),
            alert=True
        )
        job_doc.cost_recognised = 1
        job_doc.total_recognised_cost = 0
        return

    # Update job with cost recognition details
    job_doc.cost_recognised = 1
    job_doc.cost_recognition_journal_entry = je_name
    job_doc.total_recognised_cost = total_recognized


def reverse_cost_recognition(job_doc):
    """
    Reverse cost recognition when a job is cancelled.
    Cancels the main cost recognition JE and any late-invoice cost recognition JEs.

    Args:
        job_doc: The job document being cancelled
    """
    if not job_doc.cost_recognised:
        return

    if job_doc.cost_recognition_journal_entry:
        je = frappe.get_doc("Journal Entry", job_doc.cost_recognition_journal_entry)
        if je.docstatus == 1:
            je.flags.ignore_permissions = True
            je.cancel()
            frappe.msgprint(
                _("Cost Recognition Journal Entry {0} cancelled").format(
                    job_doc.cost_recognition_journal_entry
                ),
                alert=True
            )

    # Also cancel any late-invoice cost recognition JEs (submitted after job recognition)
    link_field = JOB_LINK_FIELD_MAP.get(job_doc.doctype)
    linked_pi_names = frappe.get_all(
        "Purchase Invoice",
        filters={link_field: job_doc.name},
        pluck="name"
    ) if link_field else []
    for pi_name in linked_pi_names:
        late_je_name = frappe.db.get_value("Purchase Invoice", pi_name, "recognition_journal_entry")
        if late_je_name:
            late_je = frappe.get_doc("Journal Entry", late_je_name)
            if late_je.docstatus == 1:
                late_je.flags.ignore_permissions = True
                late_je.cancel()
            frappe.db.set_value("Purchase Invoice", pi_name,
                "recognition_journal_entry", None, update_modified=False)

    # Reset cost recognition fields
    job_doc.cost_recognised = 0
    job_doc.cost_recognition_journal_entry = None
    job_doc.total_recognised_cost = 0


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
    
    # Guard: do not double-recognise if this invoice already has a recognition JE
    if frappe.db.get_value("Sales Invoice", invoice_doc.name, "recognition_journal_entry"):
        return

    job_doc = frappe.get_doc(job_doctype, job_reference)

    # Check if job already has revenue recognized
    if not job_doc.revenue_recognised or not job_doc.revenue_recognised_on:
        return

    # Check if invoice has zero amount - skip recognition
    invoice_amount = flt(invoice_doc.grand_total)
    if invoice_amount <= 0:
        frappe.msgprint(
            _("Sales Invoice {0} has zero amount. Skipping revenue recognition.").format(invoice_doc.name),
            alert=True
        )
        return

    # Create immediate recognition for this invoice — use today, not original recognition date,
    # to avoid posting into a locked accounting period.
    je_name, amount = create_single_invoice_recognition_je(
        job_doc,
        invoice_doc,
        nowdate(),
        service_type
    )

    if not je_name:
        # Nothing parked in WIP (e.g. pass-through-only invoice) — nothing to recognize
        frappe.msgprint(
            _("Sales Invoice {0} has no WIP Revenue balance. Skipping revenue recognition.").format(
                invoice_doc.name
            ),
            alert=True
        )
        return

    # Safe increment — re-read from DB to avoid overwriting a concurrent update
    current_total = flt(frappe.db.get_value(job_doctype, job_reference, "total_recognised_revenue"))
    frappe.db.set_value(job_doctype, job_reference,
        "total_recognised_revenue", current_total + amount,
        update_modified=False)

    # Store JE reference on the invoice so cancellation can find and reverse it
    invoice_doc.db_set("recognition_journal_entry", je_name, update_modified=False)

    frappe.msgprint(
        _("Late invoice revenue recognized immediately. Journal Entry: {0}").format(
            get_link_to_form("Journal Entry", je_name)
        ),
        alert=True
    )


def handle_late_purchase_invoice_submission(invoice_doc, job_doctype, job_link_field, service_type):
    """
    Handle submission of a purchase invoice after the linked job is already recognized.
    Creates an immediate cost recognition JE for this invoice.

    Args:
        invoice_doc: The Purchase Invoice being submitted
        job_doctype: The job doctype (e.g., 'Forwarding Job')
        job_link_field: The custom field linking to the job
        service_type: Service type for cost account
    """
    if not is_revenue_recognition_enabled():
        return

    job_reference = getattr(invoice_doc, job_link_field, None)
    if not job_reference:
        return

    # Guard: do not double-recognise if this invoice already has a recognition JE
    if frappe.db.get_value("Purchase Invoice", invoice_doc.name, "recognition_journal_entry"):
        return

    job_doc = frappe.get_doc(job_doctype, job_reference)

    if not job_doc.cost_recognised or not job_doc.revenue_recognised_on:
        return

    invoice_amount = flt(invoice_doc.grand_total)
    if invoice_amount <= 0:
        frappe.msgprint(
            _("Purchase Invoice {0} has zero amount. Skipping cost recognition.").format(invoice_doc.name),
            alert=True
        )
        return

    # Use today, not original recognition date, to avoid posting into a locked accounting period.
    je_name, amount = create_cost_recognition_journal_entry(
        job_doc,
        [invoice_doc],
        nowdate(),
        service_type
    )

    if not je_name:
        # Nothing parked in WIP (e.g. pass-through-only invoice) — nothing to recognize
        frappe.msgprint(
            _("Purchase Invoice {0} has no WIP Cost balance. Skipping cost recognition.").format(
                invoice_doc.name
            ),
            alert=True
        )
        return

    # Safe increment — re-read from DB to avoid overwriting a concurrent update
    current_total = flt(frappe.db.get_value(job_doctype, job_reference, "total_recognised_cost"))
    frappe.db.set_value(job_doctype, job_reference,
        "total_recognised_cost", current_total + amount,
        update_modified=False)

    # Store JE reference on the invoice so cancellation can find and reverse it
    invoice_doc.db_set("recognition_journal_entry", je_name, update_modified=False)

    frappe.msgprint(
        _("Late purchase invoice cost recognized immediately. Journal Entry: {0}").format(
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
    
    # --- Fallback: invoice was submitted AFTER job recognition (has its own recognition JE) ---
    late_je_name = getattr(invoice_doc, "recognition_journal_entry", None)
    if late_je_name:
        late_je = frappe.get_doc("Journal Entry", late_je_name)
        late_amount = sum(
            flt(a.credit_in_account_currency)
            for a in late_je.accounts
            if flt(a.credit_in_account_currency) > 0
        )
        if late_je.docstatus == 1:
            late_je.flags.ignore_permissions = True
            late_je.cancel()
        job_doc.total_recognised_revenue = flt(job_doc.total_recognised_revenue) - late_amount
        job_doc.flags.ignore_validate_update_after_submit = True
        job_doc.save()
        frappe.msgprint(
            _("Late-invoice recognition Journal Entry {0} cancelled for invoice {1}").format(
                get_link_to_form("Journal Entry", late_je_name), invoice_doc.name
            ),
            alert=True
        )
        return

    # --- Primary path: invoice was present at job submission (line in main recognition JE) ---
    je_name = job_doc.revenue_recognition_journal_entry
    if not je_name:
        return

    je = frappe.get_doc("Journal Entry", je_name)

    # Collect every line of the main JE belonging to this invoice. New-format JEs
    # have one WIP line + one line per income account; old-format JEs have one
    # Dr/Cr pair — swapping each matched line reverses both correctly.
    matched_lines = [
        account for account in je.accounts
        if remark_matches_invoice(account.user_remark, invoice_doc.name)
    ]

    # Recognized amount for this invoice = sum of its income-side (credit) lines
    invoice_amount = sum(
        flt(account.credit_in_account_currency) for account in matched_lines
    )

    if invoice_amount > 0:
        # Create partial reversal for this invoice, mirroring the original lines
        reversal_je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": nowdate(),
            "company": job_doc.company,
            "user_remark": _("Reversal for cancelled Invoice {0}").format(invoice_doc.name),
            "accounts": [
                {
                    "account": account.account,
                    "debit_in_account_currency": flt(account.credit_in_account_currency),
                    "credit_in_account_currency": flt(account.debit_in_account_currency),
                    "cost_center": account.cost_center,
                    # mirror the original remark so the reversal line keeps the
                    # job/ref/charge context and stays discoverable by job name
                    "user_remark": _("Reversal: {0}").format(account.user_remark or ""),
                }
                for account in matched_lines
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


def handle_purchase_invoice_cancellation(invoice_doc, job_doctype, job_link_field, service_type):
    """
    Handle cancellation of a purchase invoice linked to a recognized job.
    Creates a reversal JE for the recognized cost portion.
    
    Args:
        invoice_doc: The Purchase Invoice being cancelled
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
    
    if not job_doc.cost_recognised:
        return
    
    # --- Fallback: invoice was submitted AFTER job recognition (has its own recognition JE) ---
    late_je_name = getattr(invoice_doc, "recognition_journal_entry", None)
    if late_je_name:
        late_je = frappe.get_doc("Journal Entry", late_je_name)
        late_amount = sum(
            flt(a.debit_in_account_currency)
            for a in late_je.accounts
            if flt(a.debit_in_account_currency) > 0
        )
        if late_je.docstatus == 1:
            late_je.flags.ignore_permissions = True
            late_je.cancel()
        job_doc.total_recognised_cost = flt(job_doc.total_recognised_cost) - late_amount
        job_doc.flags.ignore_validate_update_after_submit = True
        job_doc.save()
        frappe.msgprint(
            _("Late-invoice cost recognition Journal Entry {0} cancelled for invoice {1}").format(
                get_link_to_form("Journal Entry", late_je_name), invoice_doc.name
            ),
            alert=True
        )
        return

    # --- Primary path: invoice was present at job submission (line in main cost recognition JE) ---
    je_name = job_doc.cost_recognition_journal_entry
    if not je_name:
        return

    je = frappe.get_doc("Journal Entry", je_name)

    # Collect every line of the main JE belonging to this invoice. New-format JEs
    # have one WIP line + one line per expense account; old-format JEs have one
    # Dr/Cr pair — swapping each matched line reverses both correctly.
    matched_lines = [
        account for account in je.accounts
        if remark_matches_invoice(account.user_remark, invoice_doc.name)
    ]

    # Recognized amount for this invoice = sum of its expense-side (debit) lines
    invoice_amount = sum(
        flt(account.debit_in_account_currency) for account in matched_lines
    )

    if invoice_amount > 0:
        # Create partial reversal for this invoice, mirroring the original lines
        reversal_je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": nowdate(),
            "company": job_doc.company,
            "user_remark": _("Cost Reversal for cancelled Invoice {0}").format(invoice_doc.name),
            "accounts": [
                {
                    "account": account.account,
                    "debit_in_account_currency": flt(account.credit_in_account_currency),
                    "credit_in_account_currency": flt(account.debit_in_account_currency),
                    "cost_center": account.cost_center,
                    # mirror the original remark so the reversal line keeps the
                    # job/ref/charge context and stays discoverable by job name
                    "user_remark": _("Reversal: {0}").format(account.user_remark or ""),
                }
                for account in matched_lines
            ],
        })

        reversal_je.flags.ignore_permissions = True
        reversal_je.insert()
        reversal_je.submit()

        # Update job's total
        job_doc.total_recognised_cost = flt(job_doc.total_recognised_cost) - invoice_amount
        job_doc.flags.ignore_validate_update_after_submit = True
        job_doc.save()

        frappe.msgprint(
            _("Cost reversal Journal Entry {0} created for cancelled invoice").format(
                get_link_to_form("Journal Entry", reversal_je.name)
            ),
            alert=True
        )


# Sales Invoice handlers
def on_sales_invoice_submit(doc, method=None):
    """Hook called when Sales Invoice is submitted."""
    job_doctype, job_name, link_field, service_type = get_recognition_job_reference(doc)
    if job_name:
        handle_late_invoice_submission(doc, job_doctype, link_field, service_type)


def set_wip_revenue_account(doc, method=None):
    """
    Hook called on Sales Invoice validate.
    Snapshots each item's natural income account and routes it to WIP Revenue
    for job-linked invoices.
    """
    validate_invoice_income_account(doc)


def on_sales_invoice_cancel_for_recognition(doc, method=None):
    """Hook called when Sales Invoice is cancelled - handle recognition reversal."""
    job_doctype, job_name, link_field, service_type = get_recognition_job_reference(doc)
    if job_name:
        handle_invoice_cancellation(doc, job_doctype, link_field, service_type)


# Purchase Invoice handlers
def set_wip_cost_account(doc, method=None):
    """
    Hook called on Purchase Invoice validate.
    Snapshots each item's natural expense account and routes it to WIP Cost
    for job-linked invoices.
    """
    validate_purchase_invoice_expense_account(doc)


def on_purchase_invoice_submit(doc, method=None):
    """Hook called when Purchase Invoice is submitted."""
    job_doctype, job_name, link_field, service_type = get_recognition_job_reference(doc)
    if job_name:
        handle_late_purchase_invoice_submission(doc, job_doctype, link_field, service_type)


def on_purchase_invoice_cancel_for_recognition(doc, method=None):
    """Hook called when Purchase Invoice is cancelled - handle cost recognition reversal."""
    job_doctype, job_name, link_field, service_type = get_recognition_job_reference(doc)
    if job_name:
        handle_purchase_invoice_cancellation(doc, job_doctype, link_field, service_type)
