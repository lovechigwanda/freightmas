# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""
Force is_private on every existing File attached to a job or invoice
doctype, ahead of the Client Portal launch.

The portal never links customers to a raw /private/files/<name> URL (see
freightmas/portal/api/documents.py) — every download goes through a
customer-scope check first. That guarantee is worthless if a File is
public, since public file_urls are directly guessable/enumerable and
bypass the portal's checks entirely. New uploads are covered going
forward by the File.before_insert hook in freightmas.portal.attachments;
this patch backfills documents that already exist.
"""

import frappe

from freightmas.portal.attachments import PROTECTED_DOCTYPES


def execute():
	frappe.db.set_value(
		"File",
		{"attached_to_doctype": ["in", PROTECTED_DOCTYPES], "is_private": 0},
		"is_private",
		1,
	)
