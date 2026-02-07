"""
Migrate Clearing Job charges from single `clearing_charges` table
to the three-table architecture:
  - clearing_costing_charges  (quoted/planned)
  - clearing_revenue_charges  (working revenue)
  - clearing_cost_charges     (working cost)
"""

import frappe
from frappe.utils import flt


def execute():
    # Check if old clearing_charges table still has data
    if not frappe.db.table_exists("tabClearing Charges"):
        return

    old_rows = frappe.db.sql(
        """
        SELECT * FROM `tabClearing Charges`
        WHERE parenttype = 'Clearing Job'
        ORDER BY parent, idx
        """,
        as_dict=True,
    )

    if not old_rows:
        return

    # Group rows by parent job
    jobs = {}
    for row in old_rows:
        jobs.setdefault(row.parent, []).append(row)

    migrated_count = 0

    for job_name, rows in jobs.items():
        # Check if new tables already have data (avoid double migration)
        existing_costing = frappe.db.count(
            "Clearing Costing Charges",
            filters={"parent": job_name, "parenttype": "Clearing Job"},
        )
        if existing_costing > 0:
            continue

        costing_idx = 0
        revenue_idx = 0
        cost_idx = 0

        for row in rows:
            charge = row.get("charge")
            description = row.get("description")
            qty = row.get("qty") or 1
            sell_rate = flt(row.get("sell_rate"))
            buy_rate = flt(row.get("buy_rate"))
            revenue_amount = flt(row.get("revenue_amount"))
            cost_amount = flt(row.get("cost_amount"))
            customer = row.get("customer")
            supplier = row.get("supplier")

            # 1. Always copy to costing charges (the planned/quoted table)
            costing_idx += 1
            margin_amount = flt(revenue_amount - cost_amount, 2)
            margin_percentage = (
                flt((margin_amount / revenue_amount) * 100, 2)
                if revenue_amount > 0
                else 0
            )

            costing_doc = frappe.get_doc(
                {
                    "doctype": "Clearing Costing Charges",
                    "parent": job_name,
                    "parenttype": "Clearing Job",
                    "parentfield": "clearing_costing_charges",
                    "idx": costing_idx,
                    "charge": charge,
                    "description": description,
                    "qty": qty,
                    "sell_rate": sell_rate,
                    "buy_rate": buy_rate,
                    "revenue_amount": revenue_amount,
                    "cost_amount": cost_amount,
                    "customer": customer,
                    "supplier": supplier,
                    "margin_amount": margin_amount,
                    "margin_percentage": margin_percentage,
                }
            )
            costing_doc.db_insert()

            # 2. Copy to revenue charges if has sell_rate and customer
            if sell_rate > 0 and customer:
                revenue_idx += 1
                revenue_doc = frappe.get_doc(
                    {
                        "doctype": "Clearing Revenue Charges",
                        "parent": job_name,
                        "parenttype": "Clearing Job",
                        "parentfield": "clearing_revenue_charges",
                        "idx": revenue_idx,
                        "charge": charge,
                        "description": description,
                        "qty": qty,
                        "sell_rate": sell_rate,
                        "revenue_amount": revenue_amount,
                        "customer": customer,
                        "is_invoiced": row.get("is_invoiced") or 0,
                        "sales_invoice_reference": row.get(
                            "sales_invoice_reference"
                        ),
                    }
                )
                revenue_doc.db_insert()

            # 3. Copy to cost charges if has buy_rate and supplier
            if buy_rate > 0 and supplier:
                cost_idx += 1
                cost_doc = frappe.get_doc(
                    {
                        "doctype": "Clearing Cost Charges",
                        "parent": job_name,
                        "parenttype": "Clearing Job",
                        "parentfield": "clearing_cost_charges",
                        "idx": cost_idx,
                        "charge": charge,
                        "description": description,
                        "qty": qty,
                        "buy_rate": buy_rate,
                        "cost_amount": cost_amount,
                        "supplier": supplier,
                        "is_purchased": row.get("is_purchased") or 0,
                        "purchase_invoice_reference": row.get(
                            "purchase_invoice_reference"
                        ),
                    }
                )
                cost_doc.db_insert()

        # Update totals on the parent job
        # Calculate quoted totals from costing charges
        total_quoted_revenue = sum(
            flt(r.get("revenue_amount")) for r in rows
        )
        total_quoted_cost = sum(flt(r.get("cost_amount")) for r in rows)
        total_quoted_margin = flt(total_quoted_revenue - total_quoted_cost, 2)
        quoted_margin_percent = (
            flt((total_quoted_margin / total_quoted_revenue) * 100, 2)
            if total_quoted_revenue > 0
            else 0
        )

        # Calculate working totals from revenue and cost charges
        total_working_revenue = sum(
            flt(r.get("revenue_amount"))
            for r in rows
            if flt(r.get("sell_rate")) > 0 and r.get("customer")
        )
        total_working_cost = sum(
            flt(r.get("cost_amount"))
            for r in rows
            if flt(r.get("buy_rate")) > 0 and r.get("supplier")
        )
        total_working_profit = flt(total_working_revenue - total_working_cost, 2)
        profit_margin_percent = (
            flt((total_working_profit / total_working_revenue) * 100, 2)
            if total_working_revenue > 0
            else 0
        )

        # Get conversion rate for base currency totals
        conversion_rate = (
            flt(
                frappe.db.get_value(
                    "Clearing Job", job_name, "conversion_rate"
                )
            )
            or 1.0
        )

        frappe.db.set_value(
            "Clearing Job",
            job_name,
            {
                "total_quoted_revenue": total_quoted_revenue,
                "total_quoted_cost": total_quoted_cost,
                "total_quoted_margin": total_quoted_margin,
                "quoted_margin_percent": quoted_margin_percent,
                "total_quoted_revenue_base": flt(
                    total_quoted_revenue * conversion_rate, 2
                ),
                "total_quoted_cost_base": flt(
                    total_quoted_cost * conversion_rate, 2
                ),
                "total_quoted_profit_base": flt(
                    total_quoted_margin * conversion_rate, 2
                ),
                "total_working_revenue": total_working_revenue,
                "total_working_cost": total_working_cost,
                "total_working_profit": total_working_profit,
                "profit_margin_percent": profit_margin_percent,
                "total_working_revenue_base": flt(
                    total_working_revenue * conversion_rate, 2
                ),
                "total_working_base": flt(
                    total_working_cost * conversion_rate, 2
                ),
                "total_working_profit_base": flt(
                    total_working_profit * conversion_rate, 2
                ),
            },
            update_modified=False,
        )

        migrated_count += 1

    frappe.db.commit()

    if migrated_count > 0:
        frappe.log_error(
            title="Clearing Job Charges Migration",
            message=f"Successfully migrated charges for {migrated_count} Clearing Job(s) from single table to three-table architecture.",
        )
