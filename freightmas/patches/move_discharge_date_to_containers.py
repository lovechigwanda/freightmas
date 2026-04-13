import frappe


def execute():
    """Copy discharge_date and is_discharged_from_vessel from parent Clearing Job
    to each Cargo Package Details child row (for Import jobs only)."""

    jobs = frappe.get_all(
        "Clearing Job",
        filters={
            "direction": "Import",
            "discharge_date": ["is", "set"],
        },
        fields=["name", "discharge_date", "is_discharged_from_vessel"],
    )

    for job in jobs:
        frappe.db.sql(
            """
            UPDATE `tabCargo Package Details`
            SET discharge_date = %(discharge_date)s,
                is_discharged_from_vessel = %(is_discharged)s
            WHERE parent = %(parent)s
              AND parenttype = 'Clearing Job'
              AND (discharge_date IS NULL OR discharge_date = '')
            """,
            {
                "discharge_date": job.discharge_date,
                "is_discharged": job.is_discharged_from_vessel,
                "parent": job.name,
            },
        )

    frappe.db.commit()
