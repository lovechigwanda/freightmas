# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Weekly Treasury Report

An executive-level weekly report for the Managing Director showing:
1. Cash position across all bank and cash accounts
2. Receipts & payments summary
3. Top receipts (money in) by party
4. Top payments (money out) by party
5. Expense category breakdown
6. Overdue debtors (accounts receivable aging)
7. Overdue creditors (accounts payable aging)
8. Mini cash flow statement (operating / investing / financing)
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, formatdate


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOP_N = 10  # Number of top parties to show in receipts/payments/debtors/creditors


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)
    derive_dates(filters)

    columns = get_columns(filters)

    data = []
    data += build_cash_position(filters)
    data += build_receipts_payments_summary(filters)
    data += build_top_receipts(filters)
    data += build_top_payments(filters)
    data += build_expense_categories(filters)
    data += build_overdue_debtors(filters)
    data += build_overdue_creditors(filters)
    data += build_mini_cashflow(filters)

    report_summary = get_report_summary(filters)
    chart = get_chart(filters)

    return columns, data, None, chart, report_summary


# ---------------------------------------------------------------------------
# Filters / validation
# ---------------------------------------------------------------------------

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("week_ending_date"):
        frappe.throw(_("Week Ending Date is required"))


def derive_dates(filters):
    """Compute week_start and week_end from the selected week ending date."""
    filters.week_end = getdate(filters.week_ending_date)
    filters.week_start = add_days(filters.week_end, -6)

    # Comparison period
    comparison = filters.get("comparison_period")
    if comparison == "Previous Week":
        filters.comp_end = add_days(filters.week_start, -1)
        filters.comp_start = add_days(filters.comp_end, -6)
    elif comparison == "Same Week Last Month":
        filters.comp_end = add_days(filters.week_end, -28)
        filters.comp_start = add_days(filters.comp_end, -6)
    else:
        filters.comp_start = None
        filters.comp_end = None


# ---------------------------------------------------------------------------
# Columns — unified schema for all sections
# ---------------------------------------------------------------------------

def get_columns(filters):
    currency = _get_currency(filters)
    cols = [
        {"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 180},
        {"label": _("Description"), "fieldname": "label", "fieldtype": "Data", "width": 260},
        {
            "label": _("Amount ({0})").format(currency),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 170,
        },
        {
            "label": _("Opening / Previous ({0})").format(currency),
            "fieldname": "amount_2",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 170,
        },
        {
            "label": _("Movement / Change ({0})").format(currency),
            "fieldname": "amount_3",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 160,
        },
        {"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 80},
        {"label": _("Party"), "fieldname": "party", "fieldtype": "Data", "width": 200},
    ]
    return cols


# ---------------------------------------------------------------------------
# Helper: row constructors
# ---------------------------------------------------------------------------

def _header_row(section, label):
    return {"section": section, "label": label, "row_type": "header",
            "amount": None, "amount_2": None, "amount_3": None, "count": None, "party": ""}


def _data_row(section, label, amount=None, amount_2=None, amount_3=None, count=None, party=""):
    return {"section": section, "label": label, "row_type": "data",
            "amount": amount, "amount_2": amount_2, "amount_3": amount_3,
            "count": count, "party": party}


def _subtotal_row(section, label, amount=None, amount_2=None, amount_3=None, count=None):
    return {"section": section, "label": label, "row_type": "subtotal",
            "amount": amount, "amount_2": amount_2, "amount_3": amount_3,
            "count": count, "party": ""}


def _spacer_row():
    return {"section": "", "label": "", "row_type": "spacer",
            "amount": None, "amount_2": None, "amount_3": None, "count": None, "party": ""}


# ---------------------------------------------------------------------------
# SECTION 1 — Cash Position Summary
# ---------------------------------------------------------------------------

def _get_balance_at_date(filters, as_of_date):
    """Return list of {account, account_name, account_type, balance} for Cash/Bank accounts."""
    return frappe.db.sql("""
        SELECT
            gle.account,
            acc.account_name,
            acc.account_type,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date <= %(as_of_date)s
            AND gle.is_cancelled = 0
        GROUP BY gle.account, acc.account_name, acc.account_type
        ORDER BY acc.account_type, acc.account_name
    """, {"company": filters.company, "as_of_date": as_of_date}, as_dict=True)


def build_cash_position(filters):
    section = "1. Cash Position"
    rows = [_header_row(section, "Cash & Bank Balances")]

    end_balances = _get_balance_at_date(filters, filters.week_end)
    start_map = {}
    for r in _get_balance_at_date(filters, add_days(filters.week_start, -1)):
        start_map[r.account] = flt(r.balance, 2)

    total_end = 0
    total_start = 0
    for row in end_balances:
        bal_end = flt(row.balance, 2)
        bal_start = start_map.get(row.account, 0)
        movement = flt(bal_end - bal_start, 2)
        total_end += bal_end
        total_start += bal_start
        rows.append(_data_row(
            section,
            f"{row.account_name} ({row.account_type})",
            amount=bal_end,
            amount_2=bal_start,
            amount_3=movement,
        ))

    # Accounts that had a start balance but zero end balance
    for acct, bal_start in start_map.items():
        if not any(r.account == acct for r in end_balances) and bal_start:
            acct_info = frappe.db.get_value("Account", acct, ["account_name", "account_type"], as_dict=True)
            total_start += bal_start
            rows.append(_data_row(
                section,
                f"{acct_info.account_name} ({acct_info.account_type})" if acct_info else acct,
                amount=0,
                amount_2=bal_start,
                amount_3=flt(-bal_start, 2),
            ))

    rows.append(_subtotal_row(section, "Total Cash & Bank",
                              amount=flt(total_end, 2),
                              amount_2=flt(total_start, 2),
                              amount_3=flt(total_end - total_start, 2)))
    rows.append(_spacer_row())

    # Store for report summary
    filters._closing_balance = flt(total_end, 2)
    filters._opening_balance = flt(total_start, 2)
    return rows


# ---------------------------------------------------------------------------
# SECTION 2 — Receipts & Payments Summary
# ---------------------------------------------------------------------------

def _get_period_debits_credits(filters, from_date, to_date):
    """Total money into and out of Cash/Bank accounts for a date range."""
    result = frappe.db.sql("""
        SELECT
            SUM(gle.debit) AS total_debit,
            SUM(gle.credit) AS total_credit
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
    """, {"company": filters.company, "from_date": from_date, "to_date": to_date}, as_dict=True)

    if result:
        # For Cash/Bank accounts (Asset): debit = money IN, credit = money OUT
        return flt(result[0].total_debit, 2), flt(result[0].total_credit, 2)
    return 0, 0


def build_receipts_payments_summary(filters):
    section = "2. Receipts & Payments"
    rows = [_header_row(section, "Summary of Cash Movement")]

    receipts, payments = _get_period_debits_credits(filters, filters.week_start, filters.week_end)
    net = flt(receipts - payments, 2)

    comp_receipts, comp_payments = 0, 0
    if filters.comp_start:
        comp_receipts, comp_payments = _get_period_debits_credits(
            filters, filters.comp_start, filters.comp_end
        )

    rows.append(_data_row(section, "Total Receipts (Money In)",
                          amount=receipts,
                          amount_2=comp_receipts if filters.comp_start else None))
    rows.append(_data_row(section, "Total Payments (Money Out)",
                          amount=payments,
                          amount_2=comp_payments if filters.comp_start else None))
    rows.append(_subtotal_row(section, "Net Cash Movement",
                              amount=net,
                              amount_2=flt(comp_receipts - comp_payments, 2) if filters.comp_start else None))
    rows.append(_spacer_row())

    filters._total_receipts = receipts
    filters._total_payments = payments
    return rows


# ---------------------------------------------------------------------------
# SECTION 3 — Top Receipts
# ---------------------------------------------------------------------------

def build_top_receipts(filters):
    section = "3. Top Receipts"
    rows = [_header_row(section, f"Top {TOP_N} Receipts by Party")]

    data = frappe.db.sql("""
        SELECT
            gle.party,
            gle.party_type,
            SUM(gle.debit) AS total_received,
            COUNT(DISTINCT gle.voucher_no) AS voucher_count
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            AND gle.debit > 0
            AND IFNULL(gle.party, '') != ''
        GROUP BY gle.party, gle.party_type
        ORDER BY total_received DESC
        LIMIT %(limit)s
    """, {
        "company": filters.company,
        "from_date": filters.week_start,
        "to_date": filters.week_end,
        "limit": TOP_N,
    }, as_dict=True)

    total = 0
    for i, r in enumerate(data, 1):
        amt = flt(r.total_received, 2)
        total += amt
        rows.append(_data_row(
            section,
            f"{i}. {r.party}",
            amount=amt,
            count=r.voucher_count,
            party=r.party_type or "",
        ))

    if data:
        rows.append(_subtotal_row(section, f"Total (Top {len(data)})", amount=flt(total, 2)))
    else:
        rows.append(_data_row(section, "No receipts in this period"))

    rows.append(_spacer_row())
    return rows


# ---------------------------------------------------------------------------
# SECTION 4 — Top Payments
# ---------------------------------------------------------------------------

def build_top_payments(filters):
    section = "4. Top Payments"
    rows = [_header_row(section, f"Top {TOP_N} Payments by Party")]

    data = frappe.db.sql("""
        SELECT
            gle.party,
            gle.party_type,
            SUM(gle.credit) AS total_paid,
            COUNT(DISTINCT gle.voucher_no) AS voucher_count
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            AND gle.credit > 0
            AND IFNULL(gle.party, '') != ''
        GROUP BY gle.party, gle.party_type
        ORDER BY total_paid DESC
        LIMIT %(limit)s
    """, {
        "company": filters.company,
        "from_date": filters.week_start,
        "to_date": filters.week_end,
        "limit": TOP_N,
    }, as_dict=True)

    total = 0
    for i, r in enumerate(data, 1):
        amt = flt(r.total_paid, 2)
        total += amt
        rows.append(_data_row(
            section,
            f"{i}. {r.party}",
            amount=amt,
            count=r.voucher_count,
            party=r.party_type or "",
        ))

    if data:
        rows.append(_subtotal_row(section, f"Total (Top {len(data)})", amount=flt(total, 2)))
    else:
        rows.append(_data_row(section, "No payments in this period"))

    rows.append(_spacer_row())
    return rows


# ---------------------------------------------------------------------------
# SECTION 5 — Expense Categories Breakdown
# ---------------------------------------------------------------------------

def build_expense_categories(filters):
    section = "5. Expense Categories"
    rows = [_header_row(section, "Payments by Expense Category")]

    # Get all GL entries that hit Cash/Bank accounts on the credit side,
    # then classify by the contra (against) account's parent_account.
    data = frappe.db.sql("""
        SELECT
            IFNULL(contra_acc.parent_account, contra_acc.name) AS category_account,
            IFNULL(contra_parent.account_name, contra_acc.account_name) AS category_name,
            SUM(gle.credit) AS total_amount,
            COUNT(DISTINCT gle.voucher_no) AS voucher_count
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        INNER JOIN `tabGL Entry` contra_gle
            ON contra_gle.voucher_no = gle.voucher_no
            AND contra_gle.voucher_type = gle.voucher_type
            AND contra_gle.is_cancelled = 0
            AND contra_gle.name != gle.name
            AND contra_gle.debit > 0
        INNER JOIN `tabAccount` contra_acc ON contra_acc.name = contra_gle.account
        LEFT JOIN `tabAccount` contra_parent ON contra_parent.name = contra_acc.parent_account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            AND gle.credit > 0
        GROUP BY category_account, category_name
        ORDER BY total_amount DESC
        LIMIT 15
    """, {
        "company": filters.company,
        "from_date": filters.week_start,
        "to_date": filters.week_end,
    }, as_dict=True)

    total = 0
    for r in data:
        amt = flt(r.total_amount, 2)
        total += amt
        rows.append(_data_row(
            section,
            r.category_name or "Unclassified",
            amount=amt,
            count=r.voucher_count,
        ))

    if data:
        rows.append(_subtotal_row(section, "Total Categorised Payments", amount=flt(total, 2)))
    else:
        rows.append(_data_row(section, "No payment categories in this period"))

    rows.append(_spacer_row())
    return rows


# ---------------------------------------------------------------------------
# SECTION 6 — Overdue Debtors
# ---------------------------------------------------------------------------

def build_overdue_debtors(filters):
    section = "6. Overdue Debtors"
    rows = [_header_row(section, f"Top {TOP_N} Overdue Debtors")]

    report_date = filters.week_end

    # Outstanding per customer from GL
    gl_data = frappe.db.sql("""
        SELECT
            gl.party AS customer,
            SUM(gl.debit) - SUM(gl.credit) AS outstanding
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE gl.company = %(company)s
            AND acc.account_type = 'Receivable'
            AND gl.party_type = 'Customer'
            AND gl.is_cancelled = 0
            AND gl.posting_date <= %(report_date)s
        GROUP BY gl.party
        HAVING outstanding > 0
        ORDER BY outstanding DESC
        LIMIT %(limit)s
    """, {"company": filters.company, "report_date": report_date, "limit": TOP_N}, as_dict=True)

    total_outstanding = 0
    total_overdue = 0
    for r in gl_data:
        outstanding = flt(r.outstanding, 2)
        total_outstanding += outstanding

        # Aging: sum overdue invoices (past due date)
        overdue = _get_overdue_amount("Sales Invoice", "customer", r.customer,
                                      filters.company, report_date)
        total_overdue += overdue

        rows.append(_data_row(
            section,
            r.customer,
            amount=outstanding,
            amount_2=overdue if overdue else None,
            party="Customer",
        ))

    if gl_data:
        rows.append(_subtotal_row(section, "Total",
                                  amount=flt(total_outstanding, 2),
                                  amount_2=flt(total_overdue, 2)))
    else:
        rows.append(_data_row(section, "No outstanding debtors"))

    rows.append(_spacer_row())
    return rows


def _get_overdue_amount(doctype, party_field, party_name, company, report_date):
    """Sum outstanding_amount on submitted invoices past their due date."""
    result = frappe.db.sql("""
        SELECT IFNULL(SUM(outstanding_amount), 0) AS overdue
        FROM `tab{doctype}`
        WHERE {party_field} = %(party)s
            AND company = %(company)s
            AND docstatus = 1
            AND outstanding_amount > 0
            AND due_date < %(report_date)s
    """.format(doctype=doctype, party_field=party_field), {
        "party": party_name,
        "company": company,
        "report_date": report_date,
    }, as_dict=True)
    return flt(result[0].overdue, 2) if result else 0


# ---------------------------------------------------------------------------
# SECTION 7 — Overdue Creditors
# ---------------------------------------------------------------------------

def build_overdue_creditors(filters):
    section = "7. Overdue Creditors"
    rows = [_header_row(section, f"Top {TOP_N} Overdue Creditors")]

    report_date = filters.week_end

    gl_data = frappe.db.sql("""
        SELECT
            gl.party AS supplier,
            SUM(gl.credit) - SUM(gl.debit) AS outstanding
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE gl.company = %(company)s
            AND acc.account_type = 'Payable'
            AND gl.party_type = 'Supplier'
            AND gl.is_cancelled = 0
            AND gl.posting_date <= %(report_date)s
        GROUP BY gl.party
        HAVING outstanding > 0
        ORDER BY outstanding DESC
        LIMIT %(limit)s
    """, {"company": filters.company, "report_date": report_date, "limit": TOP_N}, as_dict=True)

    total_outstanding = 0
    total_overdue = 0
    for r in gl_data:
        outstanding = flt(r.outstanding, 2)
        total_outstanding += outstanding

        overdue = _get_overdue_amount("Purchase Invoice", "supplier", r.supplier,
                                      filters.company, report_date)
        total_overdue += overdue

        rows.append(_data_row(
            section,
            r.supplier,
            amount=outstanding,
            amount_2=overdue if overdue else None,
            party="Supplier",
        ))

    if gl_data:
        rows.append(_subtotal_row(section, "Total",
                                  amount=flt(total_outstanding, 2),
                                  amount_2=flt(total_overdue, 2)))
    else:
        rows.append(_data_row(section, "No outstanding creditors"))

    rows.append(_spacer_row())
    return rows


# ---------------------------------------------------------------------------
# SECTION 8 — Mini Cash Flow Statement
# ---------------------------------------------------------------------------

def build_mini_cashflow(filters):
    section = "8. Mini Cash Flow"
    rows = [_header_row(section, "Cash Flow Summary")]

    # Classify GL entries on Cash/Bank accounts by the root type of contra accounts
    cashflow_data = frappe.db.sql("""
        SELECT
            contra_acc.root_type AS contra_root_type,
            contra_acc.account_type AS contra_account_type,
            SUM(gle.debit) AS cash_in,
            SUM(gle.credit) AS cash_out
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        INNER JOIN `tabGL Entry` contra_gle
            ON contra_gle.voucher_no = gle.voucher_no
            AND contra_gle.voucher_type = gle.voucher_type
            AND contra_gle.is_cancelled = 0
            AND contra_gle.name != gle.name
        INNER JOIN `tabAccount` contra_acc ON contra_acc.name = contra_gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND contra_acc.account_type NOT IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
        GROUP BY contra_acc.root_type, contra_acc.account_type
    """, {
        "company": filters.company,
        "from_date": filters.week_start,
        "to_date": filters.week_end,
    }, as_dict=True)

    # Classify into Operating / Investing / Financing
    operating_in = 0
    operating_out = 0
    investing_in = 0
    investing_out = 0
    financing_in = 0
    financing_out = 0

    for r in cashflow_data:
        cash_in = flt(r.cash_in, 2)
        cash_out = flt(r.cash_out, 2)
        root = r.contra_root_type or ""
        acct_type = r.contra_account_type or ""

        if acct_type == "Fixed Asset":
            investing_in += cash_in
            investing_out += cash_out
        elif root == "Equity" or acct_type in ("Loans (Liabilities)",):
            financing_in += cash_in
            financing_out += cash_out
        else:
            # Income, Expense, Receivable, Payable, other Liability → Operating
            operating_in += cash_in
            operating_out += cash_out

    net_operating = flt(operating_in - operating_out, 2)
    net_investing = flt(investing_in - investing_out, 2)
    net_financing = flt(financing_in - financing_out, 2)
    net_total = flt(net_operating + net_investing + net_financing, 2)

    # Operating
    rows.append(_data_row(section, "Operating — Collections", amount=operating_in))
    rows.append(_data_row(section, "Operating — Payments", amount=-operating_out))
    rows.append(_subtotal_row(section, "Net Operating Activities", amount=net_operating))

    # Investing
    rows.append(_data_row(section, "Investing — Proceeds", amount=investing_in))
    rows.append(_data_row(section, "Investing — Purchases", amount=-investing_out))
    rows.append(_subtotal_row(section, "Net Investing Activities", amount=net_investing))

    # Financing
    rows.append(_data_row(section, "Financing — Inflows", amount=financing_in))
    rows.append(_data_row(section, "Financing — Outflows", amount=-financing_out))
    rows.append(_subtotal_row(section, "Net Financing Activities", amount=net_financing))

    rows.append(_spacer_row())

    # Final reconciliation
    opening = getattr(filters, "_opening_balance", 0)
    closing = getattr(filters, "_closing_balance", 0)
    rows.append(_subtotal_row(section, "Net Cash Movement", amount=net_total))
    rows.append(_data_row(section, "Opening Cash Balance", amount=opening))
    rows.append(_subtotal_row(section, "Closing Cash Balance", amount=closing))

    return rows


# ---------------------------------------------------------------------------
# Report Summary (top-line KPI cards)
# ---------------------------------------------------------------------------

def get_report_summary(filters):
    closing = getattr(filters, "_closing_balance", 0)
    opening = getattr(filters, "_opening_balance", 0)
    receipts = getattr(filters, "_total_receipts", 0)
    payments = getattr(filters, "_total_payments", 0)
    net = flt(receipts - payments, 2)

    return [
        {
            "value": closing,
            "indicator": "Green" if closing > 0 else "Red",
            "label": _("Closing Cash Balance"),
            "datatype": "Currency",
        },
        {
            "value": receipts,
            "indicator": "Blue",
            "label": _("Week Receipts"),
            "datatype": "Currency",
        },
        {
            "value": payments,
            "indicator": "Orange",
            "label": _("Week Payments"),
            "datatype": "Currency",
        },
        {
            "value": net,
            "indicator": "Green" if net >= 0 else "Red",
            "label": _("Net Movement"),
            "datatype": "Currency",
        },
    ]


# ---------------------------------------------------------------------------
# Chart — daily receipts vs payments
# ---------------------------------------------------------------------------

def get_chart(filters):
    data = frappe.db.sql("""
        SELECT
            gle.posting_date,
            SUM(gle.debit) AS receipts,
            SUM(gle.credit) AS payments
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Asset'
            AND acc.account_type IN ('Cash', 'Bank')
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
        GROUP BY gle.posting_date
        ORDER BY gle.posting_date
    """, {
        "company": filters.company,
        "from_date": filters.week_start,
        "to_date": filters.week_end,
    }, as_dict=True)

    if not data:
        return None

    labels = [formatdate(r.posting_date, "dd-MMM") for r in data]
    receipts = [flt(r.receipts, 2) for r in data]
    payments = [flt(r.payments, 2) for r in data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Receipts"), "values": receipts},
                {"name": _("Payments"), "values": payments},
            ],
        },
        "type": "bar",
        "colors": ["#36a2eb", "#ff6384"],
        "barOptions": {"spaceRatio": 0.4},
    }


# ---------------------------------------------------------------------------
# Excel & PDF Export
# ---------------------------------------------------------------------------

@frappe.whitelist()
def export_excel(filters):
    """Generate and download a formatted Excel workbook."""
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)

    filters = frappe._dict(filters)
    validate_filters(filters)
    derive_dates(filters)

    columns = get_columns(filters)

    data = []
    data += build_cash_position(filters)
    data += build_receipts_payments_summary(filters)
    data += build_top_receipts(filters)
    data += build_top_payments(filters)
    data += build_expense_categories(filters)
    data += build_overdue_debtors(filters)
    data += build_overdue_creditors(filters)
    data += build_mini_cashflow(filters)

    from freightmas.freightmas.report.report_export_utils import build_excel_file, send_excel_response

    file_bytes = build_excel_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Weekly Treasury Report",
        net_field_label="Amount",
    )
    send_excel_response(file_bytes, "Weekly_Treasury_Report.xlsx")


@frappe.whitelist()
def export_pdf(filters):
    """Generate and download a formatted PDF report."""
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)

    filters = frappe._dict(filters)
    validate_filters(filters)
    derive_dates(filters)

    columns = get_columns(filters)

    data = []
    data += build_cash_position(filters)
    data += build_receipts_payments_summary(filters)
    data += build_top_receipts(filters)
    data += build_top_payments(filters)
    data += build_expense_categories(filters)
    data += build_overdue_debtors(filters)
    data += build_overdue_creditors(filters)
    data += build_mini_cashflow(filters)

    company = filters.company
    week_label = f"{formatdate(filters.week_start, 'dd MMM yyyy')} — {formatdate(filters.week_end, 'dd MMM yyyy')}"

    html = frappe.render_template(
        "freightmas/templates/weekly_treasury_report.html",
        {
            "company": company,
            "week_label": week_label,
            "data": data,
            "closing_balance": getattr(filters, "_closing_balance", 0),
            "total_receipts": getattr(filters, "_total_receipts", 0),
            "total_payments": getattr(filters, "_total_payments", 0),
            "currency": _get_currency(filters),
            "generated_on": frappe.utils.now_datetime().strftime("%d %b %Y %H:%M"),
        },
    )

    from frappe.utils.pdf import get_pdf
    pdf_bytes = get_pdf(html, {"orientation": "Portrait", "page-size": "A4"})

    frappe.local.response.filename = "Weekly_Treasury_Report.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "pdf"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _get_currency(filters):
    if filters.get("company"):
        return frappe.get_cached_value("Company", filters.company, "default_currency")
    return frappe.defaults.get_global_default("currency") or "USD"
