# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Seed the default Job Creation Notification Email Template."""

import frappe

from freightmas.forwarding_service.notifications.job_creation_template_content import (
	JOB_CREATION_TEMPLATE_HTML,
	JOB_CREATION_TEMPLATE_NAME,
	JOB_CREATION_TEMPLATE_SUBJECT,
)


def execute():
	if frappe.db.exists("Email Template", JOB_CREATION_TEMPLATE_NAME):
		return

	doc = frappe.new_doc("Email Template")
	doc.name = JOB_CREATION_TEMPLATE_NAME
	doc.subject = JOB_CREATION_TEMPLATE_SUBJECT
	doc.use_html = 1
	doc.response_html = JOB_CREATION_TEMPLATE_HTML
	doc.insert(ignore_permissions=True)

	if not frappe.db.get_single_value("FreightMas Settings", "default_job_creation_email_template"):
		frappe.db.set_single_value(
			"FreightMas Settings",
			"default_job_creation_email_template",
			JOB_CREATION_TEMPLATE_NAME,
		)
