# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    if not filters:
        filters = {}

    validate_filters(filters)

    # Identify the COGS / Direct Expense parent accounts for this company
    cogs_accounts = get_cogs_account_filter(filters)
    if not cogs_accounts:
        frappe.msgprint(
            _("No Cost of Goods Sold or Direct Expense accounts found for {0}. "
              "Please ensure your Chart of Accounts has accounts with account_type "
              "'Cost of Goods Sold' or a group account named 'Direct Expenses'.").format(
                filters.get("company")
            )
        )
        return get_columns(filters), [], None, None, []

    filters["_cogs_accounts"] = cogs_accounts

    columns = get_columns(filters)
    data = get_data(filters)
    report_summary = get_report_summary(data)
    chart = get_chart(data, filters)

    return columns, data, None, chart, report_summary


# ----------------------------------------
# Validation
# ----------------------------------------

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("Company is required"))

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))

    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw(_("From Date cannot be after To Date"))

    if filters.get("party") and not filters.get("party_type"):
        frappe.throw(_("Please select Party Type before selecting Party"))


# ----------------------------------------
# Identify COGS / Direct Expense Accounts
# ----------------------------------------

def get_cogs_account_filter(filters):
    """
    Find all leaf expense accounts that belong to Cost of Goods Sold.

    Strategy (in order of priority):
    1. Accounts with account_type = 'Cost of Goods Sold' (and their children via lft/rgt)
    2. Group accounts named 'Direct Expenses' or 'Cost of Goods Sold' (and children)

    Returns a list of account names, or empty list if none found.
    """
    company = filters.get("company")

    # Step 1: Find COGS group accounts by account_type
    cogs_groups = frappe.db.sql("""
        SELECT name, lft, rgt
        FROM `tabAccount`
        WHERE company = %s
            AND account_type = 'Cost of Goods Sold'
    """, (company,), as_dict=True)

    # Step 2: If no account_type match, try by common group names
    if not cogs_groups:
        cogs_groups = frappe.db.sql("""
            SELECT name, lft, rgt
            FROM `tabAccount`
            WHERE company = %s
                AND root_type = 'Expense'
                AND is_group = 1
                AND (
                    account_name IN ('Cost of Goods Sold', 'Direct Expenses',
                                     'Cost of Sales', 'Direct Costs')
                    OR account_name LIKE '%%Cost of Goods Sold%%'
                    OR account_name LIKE '%%Cost of Sales%%'
                    OR account_name LIKE '%%Direct Expense%%'
                )
        """, (company,), as_dict=True)

    if not cogs_groups:
        return []

    # Step 3: Get all accounts (leaf + group) under these parents using nested set
    conditions = " OR ".join(
        [f"(acc.lft >= {g.lft} AND acc.rgt <= {g.rgt})" for g in cogs_groups]
    )

    accounts = frappe.db.sql(f"""
        SELECT name FROM `tabAccount` acc
        WHERE acc.company = %s
            AND acc.root_type = 'Expense'
            AND acc.is_group = 0
            AND ({conditions})
    """, (company,), as_list=True)

    return [a[0] for a in accounts]


# ----------------------------------------
# Columns
# ----------------------------------------

def get_columns(filters):
    currency = get_currency(filters)
    return [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200,
        },
        {
            "label": _("Account Name"),
            "fieldname": "account_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Cost Center"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 150,
        },
        {
            "label": _("Party Type"),
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Dynamic Link",
            "options": "party_type",
            "width": 180,
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 160,
        },
        {
            "label": _("Debit ({0})").format(currency),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130,
        },
        {
            "label": _("Credit ({0})").format(currency),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130,
        },
        {
            "label": _("Net Cost ({0})").format(currency),
            "fieldname": "net_cost",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 140,
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Small Text",
            "width": 220,
        },
    ]


# ----------------------------------------
# Data
# ----------------------------------------

def get_data(filters):
    conditions = get_conditions(filters)
    gl_entries = get_gl_entries(conditions, filters)

    if not gl_entries:
        return []

    group_by = filters.get("group_by", "Group by Account")

    if group_by == "Ungrouped":
        return build_ungrouped_data(gl_entries)
    else:
        return build_grouped_data(gl_entries, group_by)


def get_gl_entries(conditions, filters):
    # Build the IN clause for COGS accounts
    cogs_accounts = filters.get("_cogs_accounts", [])
    if not cogs_accounts:
        return []

    placeholders = ", ".join(["%s"] * len(cogs_accounts))

    query = """
        SELECT
            gle.posting_date,
            gle.account,
            acc.account_name,
            gle.cost_center,
            gle.party_type,
            gle.party,
            gle.voucher_type,
            gle.voucher_no,
            gle.debit,
            gle.credit,
            (gle.debit - gle.credit) AS net_cost,
            gle.remarks
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.account IN ({placeholders})
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            {conditions}
        ORDER BY gle.account, gle.posting_date, gle.voucher_no
    """.format(placeholders=placeholders, conditions=conditions)

    # Build params: positional for IN clause + named for other filters
    params = dict(filters)
    # Remove internal keys that aren't SQL params
    params.pop("_cogs_accounts", None)
    params.pop("group_by", None)
    params.pop("fiscal_year", None)

    # frappe.db.sql with both positional and named params:
    # we need to use positional for the IN clause
    # Rebuild as fully positional-safe by using %(param)s style
    # Actually, let's use a simpler approach: inline the account list safely
    escaped_accounts = ", ".join([frappe.db.escape(a) for a in cogs_accounts])

    query = """
        SELECT
            gle.posting_date,
            gle.account,
            acc.account_name,
            gle.cost_center,
            gle.party_type,
            gle.party,
            gle.voucher_type,
            gle.voucher_no,
            gle.debit,
            gle.credit,
            (gle.debit - gle.credit) AS net_cost,
            gle.remarks
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.account IN ({accounts})
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            {conditions}
        ORDER BY gle.account, gle.posting_date, gle.voucher_no
    """.format(accounts=escaped_accounts, conditions=conditions)

    return frappe.db.sql(query, params, as_dict=True)


def get_conditions(filters):
    conditions = ""

    if filters.get("cost_center"):
        conditions += " AND gle.cost_center = %(cost_center)s"

    if filters.get("account"):
        conditions += " AND gle.account = %(account)s"

    if filters.get("party_type"):
        conditions += " AND gle.party_type = %(party_type)s"

    if filters.get("party"):
        conditions += " AND gle.party = %(party)s"

    if filters.get("voucher_type"):
        conditions += " AND gle.voucher_type = %(voucher_type)s"

    return conditions


# ----------------------------------------
# Build Ungrouped Data
# ----------------------------------------

def build_ungrouped_data(gl_entries):
    data = []
    total_debit = 0
    total_credit = 0
    total_net = 0

    for entry in gl_entries:
        data.append({
            "posting_date": entry.posting_date,
            "account": entry.account,
            "account_name": entry.account_name,
            "cost_center": entry.cost_center,
            "party_type": entry.party_type,
            "party": entry.party,
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "debit": flt(entry.debit, 2),
            "credit": flt(entry.credit, 2),
            "net_cost": flt(entry.net_cost, 2),
            "remarks": entry.remarks,
        })
        total_debit += flt(entry.debit, 2)
        total_credit += flt(entry.credit, 2)
        total_net += flt(entry.net_cost, 2)

    # Grand total row
    data.append({
        "posting_date": None,
        "account": "",
        "account_name": "<b>Grand Total</b>",
        "cost_center": "",
        "party_type": "",
        "party": "",
        "voucher_type": "",
        "voucher_no": "",
        "debit": flt(total_debit, 2),
        "credit": flt(total_credit, 2),
        "net_cost": flt(total_net, 2),
        "remarks": "",
        "is_group_total": 1,
    })

    return data


# ----------------------------------------
# Build Grouped Data
# ----------------------------------------

GROUP_FIELD_MAP = {
    "Group by Account": "account",
    "Group by Cost Center": "cost_center",
    "Group by Party": "party",
    "Group by Voucher Type": "voucher_type",
}

GROUP_LABEL_MAP = {
    "Group by Account": lambda e: f"{e.get('account')} - {e.get('account_name', '')}",
    "Group by Cost Center": lambda e: e.get("cost_center") or "No Cost Center",
    "Group by Party": lambda e: f"{e.get('party_type', '')}: {e.get('party', '')}" if e.get("party") else "No Party",
    "Group by Voucher Type": lambda e: e.get("voucher_type") or "Unknown",
}


def build_grouped_data(gl_entries, group_by):
    group_field = GROUP_FIELD_MAP.get(group_by, "account")
    label_fn = GROUP_LABEL_MAP.get(group_by, lambda e: e.get(group_field) or "Unknown")

    # Group entries
    grouped = {}
    group_order = []
    for entry in gl_entries:
        key = entry.get(group_field) or "Unassigned"
        if key not in grouped:
            grouped[key] = {
                "entries": [],
                "label": label_fn(entry),
                "total_debit": 0,
                "total_credit": 0,
                "total_net": 0,
            }
            group_order.append(key)

        grouped[key]["entries"].append(entry)
        grouped[key]["total_debit"] += flt(entry.debit, 2)
        grouped[key]["total_credit"] += flt(entry.credit, 2)
        grouped[key]["total_net"] += flt(entry.net_cost, 2)

    # Build data with subtotals
    data = []
    grand_debit = 0
    grand_credit = 0
    grand_net = 0

    for key in group_order:
        group = grouped[key]
        grand_debit += group["total_debit"]
        grand_credit += group["total_credit"]
        grand_net += group["total_net"]

        for entry in group["entries"]:
            data.append({
                "posting_date": entry.posting_date,
                "account": entry.account,
                "account_name": entry.account_name,
                "cost_center": entry.cost_center,
                "party_type": entry.party_type,
                "party": entry.party,
                "voucher_type": entry.voucher_type,
                "voucher_no": entry.voucher_no,
                "debit": flt(entry.debit, 2),
                "credit": flt(entry.credit, 2),
                "net_cost": flt(entry.net_cost, 2),
                "remarks": entry.remarks,
            })

        # Subtotal row for the group
        data.append({
            "posting_date": None,
            "account": "",
            "account_name": f"<b>Total: {group['label']}</b>",
            "cost_center": "",
            "party_type": "",
            "party": "",
            "voucher_type": "",
            "voucher_no": "",
            "debit": flt(group["total_debit"], 2),
            "credit": flt(group["total_credit"], 2),
            "net_cost": flt(group["total_net"], 2),
            "remarks": "",
            "is_group_total": 1,
        })

        # Blank separator row
        data.append({})

    # Grand total row
    data.append({
        "posting_date": None,
        "account": "",
        "account_name": "<b>Grand Total</b>",
        "cost_center": "",
        "party_type": "",
        "party": "",
        "voucher_type": "",
        "voucher_no": "",
        "debit": flt(grand_debit, 2),
        "credit": flt(grand_credit, 2),
        "net_cost": flt(grand_net, 2),
        "remarks": "",
        "is_group_total": 1,
    })

    return data


# ----------------------------------------
# Report Summary
# ----------------------------------------

def get_report_summary(data):
    if not data:
        return []

    grand_total_row = None
    for row in reversed(data):
        if row.get("is_group_total") and row.get("account_name") and "Grand Total" in row.get("account_name", ""):
            grand_total_row = row
            break

    if not grand_total_row:
        return []

    total_debit = flt(grand_total_row.get("debit", 0), 2)
    total_credit = flt(grand_total_row.get("credit", 0), 2)
    net_cost = flt(grand_total_row.get("net_cost", 0), 2)
    transaction_count = sum(1 for row in data if row.get("voucher_no") and not row.get("is_group_total"))

    return [
        {
            "value": total_debit,
            "indicator": "Red",
            "label": _("Total Cost of Sales (Debit)"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": total_credit,
            "indicator": "Green",
            "label": _("Returns / Adjustments (Credit)"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": net_cost,
            "indicator": "Orange",
            "label": _("Net Cost of Sales"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": transaction_count,
            "indicator": "Grey",
            "label": _("Transactions"),
            "datatype": "Int",
        },
    ]


# ----------------------------------------
# Chart
# ----------------------------------------

def get_chart(data, filters):
    if not data:
        return None

    account_costs = {}
    for row in data:
        if row.get("is_group_total") and row.get("account_name"):
            label = row["account_name"]
            if "Grand Total" in label:
                continue
            clean_label = label.replace("<b>", "").replace("</b>", "").replace("Total: ", "")
            net = flt(row.get("net_cost", 0), 2)
            if net != 0:
                account_costs[clean_label] = net

    if not account_costs:
        return None

    sorted_items = sorted(account_costs.items(), key=lambda x: abs(x[1]), reverse=True)[:15]

    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Net Cost of Sales"),
                    "values": values,
                }
            ],
        },
        "type": "bar",
        "colors": ["#ff5858"],
        "barOptions": {"spaceRatio": 0.4},
    }


# ----------------------------------------
# Utilities
# ----------------------------------------

def get_currency(filters):
    if filters.get("company"):
        return frappe.get_cached_value("Company", filters["company"], "default_currency")
    return frappe.defaults.get_global_default("currency") or "USD"


# ----------------------------------------
# Excel & PDF Export
# ----------------------------------------

@frappe.whitelist()
def export_excel(filters):
    """Generate and download a formatted Excel report."""
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)

    validate_filters(filters)

    cogs_accounts = get_cogs_account_filter(filters)
    if not cogs_accounts:
        frappe.throw(_("No Cost of Goods Sold accounts found for this company."))

    filters["_cogs_accounts"] = cogs_accounts
    columns = get_columns(filters)
    data = get_data(filters)

    from freightmas.freightmas.report.report_export_utils import build_excel_file, send_excel_response

    file_bytes = build_excel_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Cost of Sales Detail Report",
        net_field_label="Net Cost of Sales",
    )
    send_excel_response(file_bytes, "Cost_of_Sales_Detail_Report.xlsx")


@frappe.whitelist()
def export_pdf(filters):
    """Generate and download a formatted PDF report."""
    import json
    if isinstance(filters, str):
        filters = json.loads(filters)

    validate_filters(filters)

    cogs_accounts = get_cogs_account_filter(filters)
    if not cogs_accounts:
        frappe.throw(_("No Cost of Goods Sold accounts found for this company."))

    filters["_cogs_accounts"] = cogs_accounts
    columns = get_columns(filters)
    data = get_data(filters)

    from freightmas.freightmas.report.report_export_utils import build_pdf_file, send_pdf_response

    file_bytes = build_pdf_file(
        filters=filters,
        data=data,
        columns=columns,
        report_title="Cost of Sales Detail Report",
        net_fieldname="net_cost",
    )
    send_pdf_response(file_bytes, "Cost_of_Sales_Detail_Report.pdf")
