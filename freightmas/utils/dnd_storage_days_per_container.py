import frappe
from frappe.utils import getdate

def calculate_dnd_and_storage_days_detailed(job, cargo_packages=None, today=None):
    """
    Calculate total and per-container DND and storage days for a Clearing Job.
    Returns:
        (total_dnd_days, total_storage_days, container_breakdown): 
            tuple of ints and a list of dicts
    """
    if today is None:
        today = frappe.utils.nowdate()
    today_dt = getdate(today)

    if cargo_packages is None:
        cargo_packages = frappe.get_all(
            "Cargo Package Details",
            filters={"parent": job["name"], "parenttype": "Clearing Job"},
            fields=[
                "name",  # Add this to uniquely identify the row
                "to_be_returned", "is_loaded", "is_returned",
                "gate_in_empty_date", "gate_out_full_date",
                "pick_up_empty_date", "gate_in_full_date",
                "is_loaded_on_vessel", "loaded_on_vessel_date"
            ]
        )

    direction = job.get("direction", "Import")
    dnd_free_days = int(job.get("dnd_free_days") or 0)
    port_free_days = int(job.get("port_free_days") or 0)

    total_dnd_days = 0
    total_storage_days = 0
    container_breakdown = []

    if direction == "Export":
        for row in cargo_packages:
            row_id = row.get("name", "")
            pick_up_empty_date = getdate(row.get("pick_up_empty_date"))
            gate_in_full_date = getdate(row.get("gate_in_full_date"))
            is_loaded_on_vessel = int(row.get("is_loaded_on_vessel") or 0)
            loaded_on_vessel_date = getdate(row.get("loaded_on_vessel_date"))

            end_date = loaded_on_vessel_date if is_loaded_on_vessel and loaded_on_vessel_date else today_dt

            cargo_dnd_days = max((end_date - pick_up_empty_date).days - dnd_free_days, 0) if pick_up_empty_date else 0
            cargo_storage_days = max((end_date - gate_in_full_date).days - port_free_days, 0) if gate_in_full_date else 0

            total_dnd_days += cargo_dnd_days
            total_storage_days += cargo_storage_days

            container_breakdown.append({
                "cargo_package": row_id,
                "dnd_days": cargo_dnd_days,
                "storage_days": cargo_storage_days
            })

    else:  # Import
        discharge_date = getdate(job.get("discharge_date"))
        for row in cargo_packages:
            row_id = row.get("name", "")
            to_be_returned = int(row.get("to_be_returned") or 0)
            is_loaded = int(row.get("is_loaded") or 0)
            is_returned = int(row.get("is_returned") or 0)
            gate_in_empty_date = getdate(row.get("gate_in_empty_date"))
            gate_out_full_date = getdate(row.get("gate_out_full_date"))

            if to_be_returned:
                dnd_end_date = gate_in_empty_date if is_loaded and is_returned and gate_in_empty_date else today_dt
            else:
                dnd_end_date = gate_out_full_date if is_loaded and gate_out_full_date else today_dt

            storage_end_date = gate_out_full_date if is_loaded and gate_out_full_date else today_dt

            cargo_dnd_days = max((dnd_end_date - discharge_date).days - dnd_free_days, 0) if discharge_date else 0
            cargo_storage_days = max((storage_end_date - discharge_date).days - port_free_days, 0) if discharge_date else 0

            total_dnd_days += cargo_dnd_days
            total_storage_days += cargo_storage_days

            container_breakdown.append({
                "cargo_package": row_id,
                "dnd_days": cargo_dnd_days,
                "storage_days": cargo_storage_days
            })

    return total_dnd_days, total_storage_days, container_breakdown
