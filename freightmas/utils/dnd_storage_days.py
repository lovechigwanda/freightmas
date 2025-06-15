import frappe
from frappe.utils import getdate

def calculate_dnd_and_storage_days(job, cargo_packages=None, today=None):
    """
    Calculate total DND and storage days for a Clearing Job (Import or Export).
    Args:
        job: dict, parent document (Clearing Job)
        cargo_packages: optional, list of dicts for child table rows
        today: optional, date string (YYYY-MM-DD)
    Returns:
        (total_dnd_days, total_storage_days): tuple of ints
    """
    if today is None:
        today = frappe.utils.nowdate()
    today_dt = getdate(today)

    if cargo_packages is None:
        cargo_packages = frappe.get_all(
            "Cargo Package Details",
            filters={"parent": job["name"], "parenttype": "Clearing Job"},
            fields=[
                "to_be_returned", "is_loaded", "is_returned",
                "gate_in_empty_date", "gate_out_full_date",
                "pick_up_empty_date", "gate_in_full_date",
                "is_loaded_on_vessel", "loaded_on_vessel_date"
            ]
        )

    def get_end_date(preferred_date, fallback=today_dt):
        return getdate(preferred_date) if preferred_date else fallback

    direction = job.get("direction", "Import")
    dnd_free_days = int(job.get("dnd_free_days") or 0)
    port_free_days = int(job.get("port_free_days") or 0)

    total_dnd_days = 0
    total_storage_days = 0

    if direction == "Export":
        # EXPORT LOGIC
        for row in cargo_packages:
            pick_up_empty_date = getdate(row.get("pick_up_empty_date"))
            gate_in_full_date = getdate(row.get("gate_in_full_date"))
            is_loaded_on_vessel = int(row.get("is_loaded_on_vessel") or 0)
            loaded_on_vessel_date = getdate(row.get("loaded_on_vessel_date"))

            # Both DND and Storage end on loaded_on_vessel_date if loaded, else today
            end_date = loaded_on_vessel_date if is_loaded_on_vessel and loaded_on_vessel_date else today_dt

            # DND days
            if pick_up_empty_date:
                cargo_dnd_days = (end_date - pick_up_empty_date).days - dnd_free_days
                cargo_dnd_days = max(cargo_dnd_days, 0)
            else:
                cargo_dnd_days = 0

            # Storage days
            if gate_in_full_date:
                cargo_storage_days = (end_date - gate_in_full_date).days - port_free_days
                cargo_storage_days = max(cargo_storage_days, 0)
            else:
                cargo_storage_days = 0

            total_dnd_days += cargo_dnd_days
            total_storage_days += cargo_storage_days

    else:
        # IMPORT LOGIC
        discharge_date = getdate(job.get("discharge_date"))
        for row in cargo_packages:
            to_be_returned = int(row.get("to_be_returned") or 0)
            is_loaded = int(row.get("is_loaded") or 0)
            is_returned = int(row.get("is_returned") or 0)
            gate_in_empty_date = getdate(row.get("gate_in_empty_date"))
            gate_out_full_date = getdate(row.get("gate_out_full_date"))

            # DND end date logic
            if to_be_returned:
                if is_loaded and is_returned and gate_in_empty_date:
                    dnd_end_date = gate_in_empty_date
                else:
                    dnd_end_date = today_dt
            else:
                if is_loaded and gate_out_full_date:
                    dnd_end_date = gate_out_full_date
                else:
                    dnd_end_date = today_dt

            # Storage end date logic
            if not is_loaded:
                storage_end_date = today_dt
            elif is_loaded and gate_out_full_date:
                storage_end_date = gate_out_full_date
            else:
                storage_end_date = today_dt

            # DND days
            if dnd_end_date and discharge_date:
                cargo_dnd_days = (dnd_end_date - discharge_date).days - dnd_free_days
                cargo_dnd_days = max(cargo_dnd_days, 0)
            else:
                cargo_dnd_days = 0

            # Storage days
            if storage_end_date and discharge_date:
                cargo_storage_days = (storage_end_date - discharge_date).days - port_free_days
                cargo_storage_days = max(cargo_storage_days, 0)
            else:
                cargo_storage_days = 0

            total_dnd_days += cargo_dnd_days
            total_storage_days += cargo_storage_days

        # Fallback if no cargo packages
        if not cargo_packages:
            end_date = today_dt
            if discharge_date:
                job_dnd_days = (end_date - discharge_date).days - dnd_free_days
                job_storage_days = (end_date - discharge_date).days - port_free_days
                total_dnd_days = max(job_dnd_days, 0)
                total_storage_days = max(job_storage_days, 0)
            else:
                total_dnd_days = 0
                total_storage_days = 0

    return total_dnd_days, total_storage_days
