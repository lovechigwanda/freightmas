# freightmas/.../folder.py
# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd

import frappe
from frappe.utils import get_datetime, now_datetime
import traceback

HOME = "Home"
PARENT_FOLDER_NAME = "Forwarding Jobs"

# -------------------------
# Sanitization & naming
# -------------------------
def _sanitize_folder_name(name):
    """
    Sanitize folder name to remove problematic characters that can be
    interpreted as path separators or cause URL encoding issues.
    """
    if not name:
        return ""
    bad = ['/', '\\', '%', ':', '?', '*', '|', '"', '<', '>', '\r', '\n', '\t']
    s = str(name)
    for ch in bad:
        s = s.replace(ch, '_')
    s = s.strip(' .')
    if len(s) > 120:
        s = s[:120]
    return s

def _year_from_doc(doc):
    try:
        creation = doc.get("creation") or doc.get("date_created")
        if creation:
            year = get_datetime(creation).year
        else:
            year = now_datetime().year
    except Exception:
        year = now_datetime().year
    return str(year)

def _job_folder_name(doc):
    """
    Compose folder name including Job Name, Customer Reference and Customer Name.
    Format: JOBNAME - CUSTOMERREFERENCE - CUSTOMERNAME
    If customer_reference or customer_name is empty those parts are omitted.
    """
    ref_raw = (doc.get("customer_reference") or doc.get("reference") or "").strip()
    customer_name_raw = (doc.get("customer_name") or doc.get("customer") or "").strip()
    jobname_raw = (doc.get("name") or doc.get("job_no") or doc.get("job_name") or "").strip()

    parts = [p for p in [jobname_raw, ref_raw, customer_name_raw] if p]
    raw = " - ".join(parts)
    return _sanitize_folder_name(raw)

# -------------------------
# Folder helpers
# -------------------------
def _ensure_folder_exists(folder_name, parent_folder):
    """
    Ensure the folder exists. parent_folder may be:
      - None / empty -> treated as HOME
      - a single folder name (e.g. "Home")
      - a path like "Home/Forwarding Jobs" (multiple segments)
    This function will create any missing parent segments first and then create
    the requested folder_name under the final parent.
    Returns the full path string: "<parent_folder>/<sanitized folder_name>"
    """
    # sanitize folder_name
    folder_name = _sanitize_folder_name(folder_name)

    # normalize parent_folder: if None -> HOME, else strip spaces
    if not parent_folder:
        parent_folder = HOME
    parent_folder = parent_folder.strip()

    # If parent_folder contains '/', ensure each segment exists
    # Build segments list, e.g. ["Home", "Forwarding Jobs"]
    segments = parent_folder.split("/")
    # ensure the chain exists starting from the root "Home"
    current_parent = None
    for i, seg in enumerate(segments):
        seg = _sanitize_folder_name(seg)
        if i == 0:
            # expected to be "Home" normally; ensure Home exists as a folder doc root
            if not frappe.db.exists("File", {"is_folder": 1, "file_name": seg, "folder": None}):
                try:
                    frappe.get_doc({
                        "doctype": "File",
                        "file_name": seg,
                        "is_folder": 1,
                        "folder": None
                    }).insert(ignore_permissions=True)
                except Exception:
                    # race or existing by other path: ignore
                    frappe.log_error(traceback.format_exc(), "ensure_root_folder_error")
            current_parent = seg
        else:
            # ensure segment exists under current_parent
            if not frappe.db.exists("File", {"is_folder": 1, "file_name": seg, "folder": current_parent}):
                try:
                    frappe.get_doc({
                        "doctype": "File",
                        "file_name": seg,
                        "is_folder": 1,
                        "folder": current_parent
                    }).insert(ignore_permissions=True)
                except Exception:
                    frappe.log_error(traceback.format_exc(), "ensure_intermediate_folder_error")
            current_parent = f"{current_parent}/{seg}"

    # Now current_parent equals the normalized parent_folder path
    target_parent = current_parent or HOME

    # If the target folder already exists under that parent, return path
    if frappe.db.exists("File", {"is_folder": 1, "file_name": folder_name, "folder": target_parent}):
        return f"{target_parent}/{folder_name}"

    try:
        # create the folder under the target_parent
        frappe.get_doc({
            "doctype": "File",
            "file_name": folder_name,
            "is_folder": 1,
            "folder": target_parent
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(traceback.format_exc(), "ensure_create_final_folder_error")

    return f"{target_parent}/{folder_name}"

def _consolidate_year_folders(year):
    """
    If there are multiple folder docs named `year`, reparent them under Home/Forwarding Jobs
    and remove duplicates (by reparenting children into canonical folder).
    Returns the canonical year folder path (Home/Forwarding Jobs/<year>).
    """
    canonical_parent = _ensure_folder_exists(PARENT_FOLDER_NAME, HOME)  # returns 'Home/Forwarding Jobs'
    canonical_year_path = _ensure_folder_exists(year, canonical_parent)  # ensures Home/Forwarding Jobs/<year>

    # Find all folder docs whose file_name == year
    rows = frappe.get_all("File", filters={
        "is_folder": 1,
        "file_name": year
    }, fields=["name", "file_name", "folder"])

    # The canonical folder should have folder == canonical_parent
    canonical_folder = None
    for r in rows:
        if r.get("folder") == canonical_parent:
            canonical_folder = r
            break

    # If we found a folder at canonical_parent, reparent any others into it
    if canonical_folder:
        canonical_name = canonical_folder.get("file_name")
        canonical_full = f"{canonical_parent}/{canonical_name}"
        for r in rows:
            if r.get("name") == canonical_folder.get("name"):
                continue
            try:
                # reparent this folder doc's children - easiest is to update its folder to canonical_parent
                folder_doc = frappe.get_doc("File", r["name"])
                folder_doc.folder = canonical_parent
                # Optionally also ensure file_name equals year (likely already)
                folder_doc.file_name = year
                folder_doc.save(ignore_permissions=True)
            except Exception:
                frappe.log_error(traceback.format_exc(), f"reparent_year_folder_{r['name']}")
        return canonical_full

    # No canonical yet: ensure canonical exists and then reparent all others into it
    canonical_full = canonical_year_path
    for r in rows:
        try:
            folder_doc = frappe.get_doc("File", r["name"])
            if folder_doc.folder != canonical_parent:
                folder_doc.folder = canonical_parent
                folder_doc.file_name = year
                folder_doc.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(traceback.format_exc(), f"reparent_year_folder_{r['name']}")
    return canonical_full

def _get_year_folder_path(doc):
    """
    Ensure base and year folders exist; return canonical year folder path string 'Home/Forwarding Jobs/<YEAR>'
    This function consolidates any stray year folders into the canonical parent.
    """
    # Ensure parent base exists
    _ensure_folder_exists(PARENT_FOLDER_NAME, HOME)  # ensures Home/Forwarding Jobs is present
    year = _year_from_doc(doc)

    # Consolidate existing year folders and return canonical path
    year_folder_path = _consolidate_year_folders(year)
    return year_folder_path

def _reparent_existing_folder_to_year(job_name_prefix, year_folder, desired_name):
    """
    Finds an existing folder anywhere whose file_name starts with job_name_prefix
    and re-parents it under year_folder (and renames file_name to desired_name).
    Returns the folder_doc if found and updated, else None.
    """
    folders = frappe.get_all("File", filters={
        "is_folder": 1,
        "file_name": ["like", f"{job_name_prefix}%"]
    }, fields=["name", "file_name", "folder"], limit=1)

    if not folders:
        return None

    f = folders[0]
    try:
        folder_doc = frappe.get_doc("File", f["name"])
        # Re-parent and rename
        folder_doc.file_name = desired_name
        folder_doc.folder = year_folder
        folder_doc.save(ignore_permissions=True)
        return folder_doc
    except Exception:
        frappe.log_error(traceback.format_exc(), "_reparent_existing_folder_to_year_error")
        return None

# -------------------------
# Lazy creation: we do NOT create job folder on job insert
# -------------------------
def create_job_folder_on_insert(doc, method=None):
    """
    NO-OP for lazy creation (kept for backward compatibility).
    We intentionally do not create folders on job creation to avoid empty folders.
    Use file_on_insert to create when first attachment arrives, or run migration helper for bulk creation.
    """
    # intentionally left blank for lazy folder creation
    return

# -------------------------
# Update & rename handlers
# -------------------------
def update_job_folder_on_update(doc, method=None):
    """
    Hook: Forwarding Job on_update
    Ensure folder exists for current creation year and rename folder if desired name changed.
    This will create the job folder if it already exists elsewhere or if files exist (keeps idempotency).
    """
    try:
        year_folder = _get_year_folder_path(doc)
        desired_name = _job_folder_name(doc)
        jobname_prefix = doc.name

        # First try to find the folder under the correct year folder
        existing = frappe.get_all("File", filters={
            "is_folder": 1,
            "folder": year_folder,
            "file_name": ["like", f"{jobname_prefix}%"]
        }, fields=["name", "file_name"], limit=1)

        if existing:
            folder_doc = frappe.get_doc("File", existing[0]["name"])
            if folder_doc.file_name != desired_name or folder_doc.folder != year_folder:
                folder_doc.file_name = desired_name
                folder_doc.folder = year_folder
                folder_doc.save(ignore_permissions=True)
        else:
            # Try to find any existing folder globally that matches this job and reparent it
            found = _reparent_existing_folder_to_year(jobname_prefix, year_folder, desired_name)
            if not found:
                # If there are attached files already (maybe created by old code), ensure folder exists
                attached = frappe.get_all("File", filters={
                    "attached_to_doctype": "Forwarding Job",
                    "attached_to_name": doc.name
                }, limit=1)
                if attached:
                    _ensure_folder_exists(desired_name, year_folder)
        # Move any already-attached files into the job folder (if job folder now exists)
        _move_attached_files_to_job_folder(doc)
    except Exception:
        frappe.log_error(traceback.format_exc(), "update_job_folder_on_update_error")

def before_rename_forwarding_job(old, new, merge=False):
    """
    Hook: Forwarding Job before_rename
    Rename the folder path when the document is renamed.
    """
    try:
        if merge:
            return
        try:
            old_doc = frappe.get_doc("Forwarding Job", old)
        except Exception:
            return

        new_doc = frappe._dict(old_doc.as_dict())
        new_doc.name = new

        old_year_folder = _get_year_folder_path(old_doc)
        old_folder_name = _job_folder_name(old_doc)
        new_year_folder = _get_year_folder_path(new_doc)
        new_folder_name = _job_folder_name(new_doc)

        # Try to find the folder under the old year folder first
        folders = frappe.get_all("File", filters={
            "is_folder": 1,
            "folder": old_year_folder,
            "file_name": old_folder_name
        }, fields=["name"], limit=1)

        if folders:
            folder_doc = frappe.get_doc("File", folders[0]["name"])
            # Update the folder directly without creating a new one
            folder_doc.file_name = new_folder_name
            folder_doc.folder = new_year_folder
            folder_doc.save(ignore_permissions=True)
        else:
            # fallback: try to find any folder with prefix old job name and reparent/rename it
            _reparent_existing_folder_to_year(old, new_year_folder, new_folder_name)

        # Update attached files' folder values to the new path (if any)
        files = frappe.get_all("File", filters={
            "attached_to_doctype": "Forwarding Job",
            "attached_to_name": new
        }, fields=["name"], limit_page_length=1000)

        for f in files:
            frappe.db.set_value("File", f["name"], "folder", f"{new_year_folder}/{new_folder_name}", update_modified=False)

    except Exception:
        frappe.log_error(traceback.format_exc(), "before_rename_forwarding_job_error")

# -------------------------
# Core: move attached files (DB-only)
# -------------------------
def _move_attached_files_to_job_folder(doc):
    """
    Move File docs attached to this Forwarding Job into the job folder.
    This updates the File.folder field only (DB update), not the physical file path.
    """
    try:
        year_folder = _get_year_folder_path(doc)
        desired_name = _job_folder_name(doc)
        job_folder_path = f"{year_folder}/{desired_name}"

        files = frappe.get_all("File", filters={
            "attached_to_doctype": "Forwarding Job",
            "attached_to_name": doc.name,
            "is_folder": 0
        }, fields=["name", "folder"], limit_page_length=1000)

        # Only create folder if there are files to move
        if files:
            _ensure_folder_exists(desired_name, year_folder)
            
            for f in files:
                try:
                    if f.get("folder") == job_folder_path:
                        continue
                    frappe.db.set_value("File", f.get("name"), "folder", job_folder_path, update_modified=False)
                except Exception:
                    frappe.log_error(traceback.format_exc(), "move_attached_file_error")
    except Exception:
        frappe.log_error(traceback.format_exc(), "_move_attached_files_to_job_folder_error")

# -------------------------
# FILE hooks: create folder lazily when file attached
# -------------------------
def file_on_insert(file_doc, method=None):
    """
    Hook: File after_insert
    If a file is attached to a Forwarding Job, ensure the job folder exists (create lazily)
    and move the File doc into it (DB folder update).
    """
    try:
        if file_doc.is_folder:
            return
        if file_doc.attached_to_doctype != "Forwarding Job" or not file_doc.attached_to_name:
            return

        try:
            job = frappe.get_doc("Forwarding Job", file_doc.attached_to_name)
        except Exception:
            return

        # Build desired folder path including customer name and reference
        year_folder = _get_year_folder_path(job)
        desired_name = _job_folder_name(job)
        job_folder_path = f"{year_folder}/{desired_name}"

        # Ensure job folder exists (this creates it lazily on first attachment)
        _ensure_folder_exists(desired_name, year_folder)

        # Move just this file to the job folder if not already there
        if file_doc.folder != job_folder_path:
            frappe.db.set_value("File", file_doc.name, "folder", job_folder_path, update_modified=False)

    except Exception:
        frappe.log_error(traceback.format_exc(), "file_on_insert_error")

def file_on_update(file_doc, method=None):
    # reuse same logic
    return file_on_insert(file_doc, method)

# -------------------------
# Migration helper (optional)
# -------------------------
def organize_all_forwarding_job_files():
    """
    One-time migration helper - iterate all Forwarding Job docs and ensure folders + move files.
    Call via: bench execute freightmas.utils.forwarding_job_folder.organize_all_forwarding_job_files
    """
    try:
        jobs = frappe.get_all("Forwarding Job", fields=["name"], limit_page_length=1000)
        for j in jobs:
            try:
                doc = frappe.get_doc("Forwarding Job", j["name"])
                # only create folder if job has attachments (keeps it lazy)
                attachments = frappe.get_all("File", filters={
                    "attached_to_doctype": "Forwarding Job",
                    "attached_to_name": doc.name
                }, limit=1)
                if attachments:
                    _ensure_folder_exists(_job_folder_name(doc), _get_year_folder_path(doc))
                    _move_attached_files_to_job_folder(doc)
            except Exception:
                frappe.log_error(traceback.format_exc(), f"organize_job_{j['name']}")
    except Exception:
        frappe.log_error(traceback.format_exc(), "organize_all_forwarding_job_files_error")

# -------------------------
# Legacy wrapper hooks for backward compatibility
# -------------------------
def handle_forwarding_job_folder_creation(doc, method):
    """Legacy hook - redirects to new function"""
    if method == "after_insert":
        create_job_folder_on_insert(doc, method)
    else:
        update_job_folder_on_update(doc, method)

def handle_forwarding_job_folder_rename(doc, method, old_name, new_name, merge=False):
    """Legacy hook - redirects to new function"""
    before_rename_forwarding_job(old_name, new_name, merge)

def handle_file_move_to_job_folder(doc, method):
    """Legacy hook - redirects to new function"""
    if method == "after_insert":
        file_on_insert(doc, method)
    else:
        file_on_update(doc, method)