# freightmas/.../clearing_job_folder.py
# Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd

import frappe
from frappe.utils import get_datetime, now_datetime
import traceback

HOME = "Home"
PARENT_FOLDER_NAME = "Clearing Jobs"

# -------------------------
# Sanitization & naming
# -------------------------
def _sanitize_folder_name(name):
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
    Compose folder name: JOBNAME - CUSTOMERREFERENCE - CUSTOMERNAME
    Parts are omitted if empty.
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
    Ensure the folder exists under parent_folder (creating intermediate segments as needed).
    Returns the full path string: "<parent_folder>/<sanitized folder_name>"
    """
    folder_name = _sanitize_folder_name(folder_name)

    if not parent_folder:
        parent_folder = HOME
    parent_folder = parent_folder.strip()

    segments = parent_folder.split("/")
    current_parent = None
    for i, seg in enumerate(segments):
        seg = _sanitize_folder_name(seg)
        if i == 0:
            if not frappe.db.exists("File", {"is_folder": 1, "file_name": seg, "folder": None}):
                try:
                    frappe.get_doc({
                        "doctype": "File",
                        "file_name": seg,
                        "is_folder": 1,
                        "folder": None
                    }).insert(ignore_permissions=True)
                except Exception:
                    frappe.log_error(traceback.format_exc(), "ensure_root_folder_error")
            current_parent = seg
        else:
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

    target_parent = current_parent or HOME

    if frappe.db.exists("File", {"is_folder": 1, "file_name": folder_name, "folder": target_parent}):
        return f"{target_parent}/{folder_name}"

    try:
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
    Consolidate stray year folders under Home/Clearing Jobs.
    Returns the canonical year folder path (Home/Clearing Jobs/<year>).
    """
    canonical_parent = _ensure_folder_exists(PARENT_FOLDER_NAME, HOME)
    canonical_year_path = _ensure_folder_exists(year, canonical_parent)

    rows = frappe.get_all("File", filters={
        "is_folder": 1,
        "file_name": year
    }, fields=["name", "file_name", "folder"])

    canonical_folder = None
    for r in rows:
        if r.get("folder") == canonical_parent:
            canonical_folder = r
            break

    if canonical_folder:
        canonical_name = canonical_folder.get("file_name")
        canonical_full = f"{canonical_parent}/{canonical_name}"
        for r in rows:
            if r.get("name") == canonical_folder.get("name"):
                continue
            try:
                folder_doc = frappe.get_doc("File", r["name"])
                folder_doc.folder = canonical_parent
                folder_doc.file_name = year
                folder_doc.save(ignore_permissions=True)
            except Exception:
                frappe.log_error(traceback.format_exc(), f"reparent_year_folder_{r['name']}")
        return canonical_full

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
    """Return canonical year folder path: Home/Clearing Jobs/<YEAR>"""
    _ensure_folder_exists(PARENT_FOLDER_NAME, HOME)
    year = _year_from_doc(doc)
    return _consolidate_year_folders(year)

def _reparent_existing_folder_to_year(job_name_prefix, year_folder, desired_name):
    """
    Find an existing folder whose file_name starts with job_name_prefix and re-parent it.
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
        folder_doc.file_name = desired_name
        folder_doc.folder = year_folder
        folder_doc.save(ignore_permissions=True)
        return folder_doc
    except Exception:
        frappe.log_error(traceback.format_exc(), "_reparent_existing_folder_to_year_error")
        return None

# -------------------------
# Lazy creation: do NOT create folder on job insert
# -------------------------
def create_job_folder_on_insert(doc, method=None):
    """NO-OP for lazy creation — folder is created when first file is attached."""
    return

# -------------------------
# Update & rename handlers
# -------------------------
def update_job_folder_on_update(doc, method=None):
    """Hook: Clearing Job on_update — rename/move folder if job name or reference changed."""
    try:
        year_folder = _get_year_folder_path(doc)
        desired_name = _job_folder_name(doc)
        jobname_prefix = doc.name

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
            found = _reparent_existing_folder_to_year(jobname_prefix, year_folder, desired_name)
            if not found:
                attached = frappe.get_all("File", filters={
                    "attached_to_doctype": "Clearing Job",
                    "attached_to_name": doc.name
                }, limit=1)
                if attached:
                    _ensure_folder_exists(desired_name, year_folder)

        _move_attached_files_to_job_folder(doc)
    except Exception:
        frappe.log_error(traceback.format_exc(), "clearing_update_job_folder_on_update_error")

def before_rename_clearing_job(old, new, merge=False):
    """Hook: Clearing Job before_rename — rename the file-manager folder accordingly."""
    try:
        if merge:
            return
        try:
            old_doc = frappe.get_doc("Clearing Job", old)
        except Exception:
            return

        new_doc = frappe._dict(old_doc.as_dict())
        new_doc.name = new

        old_year_folder = _get_year_folder_path(old_doc)
        old_folder_name = _job_folder_name(old_doc)
        new_year_folder = _get_year_folder_path(new_doc)
        new_folder_name = _job_folder_name(new_doc)

        folders = frappe.get_all("File", filters={
            "is_folder": 1,
            "folder": old_year_folder,
            "file_name": old_folder_name
        }, fields=["name"], limit=1)

        if folders:
            folder_doc = frappe.get_doc("File", folders[0]["name"])
            folder_doc.file_name = new_folder_name
            folder_doc.folder = new_year_folder
            folder_doc.save(ignore_permissions=True)
        else:
            _reparent_existing_folder_to_year(old, new_year_folder, new_folder_name)

        files = frappe.get_all("File", filters={
            "attached_to_doctype": "Clearing Job",
            "attached_to_name": new
        }, fields=["name"], limit_page_length=1000)

        for f in files:
            frappe.db.set_value("File", f["name"], "folder", f"{new_year_folder}/{new_folder_name}", update_modified=False)

    except Exception:
        frappe.log_error(traceback.format_exc(), "before_rename_clearing_job_error")

# -------------------------
# Core: move attached files (DB-only)
# -------------------------
def _move_attached_files_to_job_folder(doc):
    """Move File docs attached to this Clearing Job into the job folder (DB folder update only)."""
    try:
        year_folder = _get_year_folder_path(doc)
        desired_name = _job_folder_name(doc)
        job_folder_path = f"{year_folder}/{desired_name}"

        files = frappe.get_all("File", filters={
            "attached_to_doctype": "Clearing Job",
            "attached_to_name": doc.name,
            "is_folder": 0
        }, fields=["name", "folder"], limit_page_length=1000)

        if files:
            _ensure_folder_exists(desired_name, year_folder)

            for f in files:
                try:
                    if f.get("folder") == job_folder_path:
                        continue
                    frappe.db.set_value("File", f.get("name"), "folder", job_folder_path, update_modified=False)
                except Exception:
                    frappe.log_error(traceback.format_exc(), "clearing_move_attached_file_error")
    except Exception:
        frappe.log_error(traceback.format_exc(), "clearing_move_attached_files_to_job_folder_error")

# -------------------------
# FILE hooks: create folder lazily when file attached
# -------------------------
def file_on_insert(file_doc, method=None):
    """Hook: File after_insert — lazily create Clearing Job folder and move file into it."""
    try:
        if file_doc.is_folder:
            return
        if file_doc.attached_to_doctype != "Clearing Job" or not file_doc.attached_to_name:
            return

        try:
            job = frappe.get_doc("Clearing Job", file_doc.attached_to_name)
        except Exception:
            return

        year_folder = _get_year_folder_path(job)
        desired_name = _job_folder_name(job)
        job_folder_path = f"{year_folder}/{desired_name}"

        _ensure_folder_exists(desired_name, year_folder)

        if file_doc.folder != job_folder_path:
            frappe.db.set_value("File", file_doc.name, "folder", job_folder_path, update_modified=False)

    except Exception:
        frappe.log_error(traceback.format_exc(), "clearing_file_on_insert_error")

def file_on_update(file_doc, method=None):
    return file_on_insert(file_doc, method)

# -------------------------
# Migration helper (optional)
# -------------------------
def organize_all_clearing_job_files():
    """
    One-time migration helper — iterate all Clearing Job docs and ensure folders + move files.
    Call via: bench execute freightmas.utils.clearing_job_folder.organize_all_clearing_job_files
    """
    try:
        jobs = frappe.get_all("Clearing Job", fields=["name"], limit_page_length=1000)
        for j in jobs:
            try:
                doc = frappe.get_doc("Clearing Job", j["name"])
                attachments = frappe.get_all("File", filters={
                    "attached_to_doctype": "Clearing Job",
                    "attached_to_name": doc.name
                }, limit=1)
                if attachments:
                    _ensure_folder_exists(_job_folder_name(doc), _get_year_folder_path(doc))
                    _move_attached_files_to_job_folder(doc)
            except Exception:
                frappe.log_error(traceback.format_exc(), f"organize_clearing_job_{j['name']}")
    except Exception:
        frappe.log_error(traceback.format_exc(), "organize_all_clearing_job_files_error")
