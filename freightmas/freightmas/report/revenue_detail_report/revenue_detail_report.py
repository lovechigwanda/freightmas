# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, fmt_money


def execute(filters=None):
    if not filters:
        filters = {}

    validate_filters(filters)

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
# Columns
# ----------------------------------------

def get_columns(filters):
    columns = [
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
            "label": _("Debit ({0})").format(get_currency(filters)),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130,
        },
        {
            "label": _("Credit ({0})").format(get_currency(filters)),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "width": 130,
        },
        {
            "label": _("Net Revenue ({0})").format(get_currency(filters)),
            "fieldname": "net_revenue",
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

    return columns


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
    return frappe.db.sql(
        """
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
            (gle.credit - gle.debit) AS net_revenue,
            gle.remarks,
            gle.against
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE acc.root_type = 'Income'
            AND gle.company = %(company)s
            AND gle.posting_date >= %(from_date)s
            AND gle.posting_date <= %(to_date)s
            AND gle.is_cancelled = 0
            {conditions}
        ORDER BY gle.account, gle.posting_date, gle.voucher_no
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )


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
            "net_revenue": flt(entry.net_revenue, 2),
            "remarks": entry.remarks,
        })
        total_debit += flt(entry.debit, 2)
        total_credit += flt(entry.credit, 2)
        total_net += flt(entry.net_revenue, 2)

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
        "net_revenue": flt(total_net, 2),
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
        grouped[key]["total_net"] += flt(entry.net_revenue, 2)

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
                "net_revenue": flt(entry.net_revenue, 2),
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
            "net_revenue": flt(group["total_net"], 2),
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
        "net_revenue": flt(grand_net, 2),
        "remarks": "",
        "is_group_total": 1,
    })

    return data


# ----------------------------------------
# Report Summary (coloured cards at top)
# ----------------------------------------

def get_report_summary(data):
    if not data:
        return []

    # Find the grand total row (last non-empty row with is_group_total)
    grand_total_row = None
    for row in reversed(data):
        if row.get("is_group_total") and row.get("account_name") and "Grand Total" in row.get("account_name", ""):
            grand_total_row = row
            break

    if not grand_total_row:
        return []

    total_credit = flt(grand_total_row.get("credit", 0), 2)
    total_debit = flt(grand_total_row.get("debit", 0), 2)
    net_revenue = flt(grand_total_row.get("net_revenue", 0), 2)

    # Count unique voucher entries (exclude group total and blank rows)
    transaction_count = sum(1 for row in data if row.get("voucher_no") and not row.get("is_group_total"))

    return [
        {
            "value": total_credit,
            "indicator": "Green",
            "label": _("Total Revenue (Credit)"),
            "datatype": "Currency",
            "currency": None,  # uses default
        },
        {
            "value": total_debit,
            "indicator": "Red",
            "label": _("Returns / Adjustments (Debit)"),
            "datatype": "Currency",
            "currency": None,
        },
        {
            "value": net_revenue,
            "indicator": "Blue",
            "label": _("Net Revenue"),
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
# Chart (revenue per account)
# ----------------------------------------

def get_chart(data, filters):
    if not data:
        return None

    # Collect per-account net revenue from subtotal rows
    account_revenue = {}
    for row in data:
        if row.get("is_group_total") and row.get("account_name"):
            label = row["account_name"]
            # Skip Grand Total row
            if "Grand Total" in label:
                continue
            # Clean the HTML bold tags for chart labels
            clean_label = label.replace("<b>", "").replace("</b>", "").replace("Total: ", "")
            net = flt(row.get("net_revenue", 0), 2)
            if net != 0:
                account_revenue[clean_label] = net

    if not account_revenue:
        return None

    # Sort by revenue descending, take top 15
    sorted_items = sorted(account_revenue.items(), key=lambda x: abs(x[1]), reverse=True)[:15]

    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Net Revenue"),
                    "values": values,
                }
            ],
        },
        "type": "bar",
        "colors": ["#5e64ff"],
        "barOptions": {"spaceRatio": 0.4},
    }


# ----------------------------------------
# Utilities
# ----------------------------------------

def get_currency(filters):
    if filters.get("company"):
        return frappe.get_cached_value("Company", filters["company"], "default_currency")
    return frappe.defaults.get_global_default("currency") or "USD"
