# Shared company logo helpers for portal branding and PDF generation.

from __future__ import annotations

import base64
import os

import frappe

_LOGO_MIME = {
	"png": "image/png",
	"jpg": "image/jpeg",
	"jpeg": "image/jpeg",
	"gif": "image/gif",
	"svg": "image/svg+xml",
	"webp": "image/webp",
}


def _logo_file_path(company):
	logo = frappe.db.get_value("Company", company, "company_logo")
	if not logo or not isinstance(logo, str) or not logo.startswith("/"):
		return None, None

	is_private = "/private/" in logo
	relative = logo.split("/files/", 1)[-1]
	file_path = frappe.utils.get_files_path(relative, is_private=is_private)
	if not os.path.exists(file_path):
		return None, None

	ext = logo.rsplit(".", 1)[-1].lower() if "." in logo else "png"
	mime = _LOGO_MIME.get(ext, "image/png")
	filename = os.path.basename(relative) or f"logo.{ext}"
	return file_path, {"mime": mime, "filename": filename, "ext": ext}


def read_company_logo_bytes(company):
	"""Return (bytes, content_type, filename) for the company logo, or None."""
	file_path, meta = _logo_file_path(company)
	if not file_path:
		return None
	try:
		with open(file_path, "rb") as fh:
			return fh.read(), meta["mime"], meta["filename"]
	except OSError:
		return None


def company_logo_data_uri(company):
	"""Base64 data URI for inline embedding in PDF/HTML (no network fetch)."""
	result = read_company_logo_bytes(company)
	if not result:
		return None
	content, mime, _filename = result
	encoded = base64.b64encode(content).decode()
	return f"data:{mime};base64,{encoded}"
