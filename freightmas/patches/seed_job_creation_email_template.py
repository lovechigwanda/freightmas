# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Seed job creation Email Templates."""

import frappe

from freightmas.forwarding_service.notifications.job_creation_template_content import (
	FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	FORWARDING_JOB_CREATION_TEMPLATE_NAME,
	FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
	JOB_CREATION_TEMPLATE_HTML,
	JOB_CREATION_TEMPLATE_NAME,
	JOB_CREATION_TEMPLATE_SUBJECT,
)


def _seed_template(name, subject, response_html):
	if frappe.db.exists("Email Template", name):
		return
	doc = frappe.new_doc("Email Template")
	doc.name = name
	doc.subject = subject
	doc.use_html = 1
	doc.response_html = response_html
	doc.insert(ignore_permissions=True)


def execute():
	_seed_template(JOB_CREATION_TEMPLATE_NAME, JOB_CREATION_TEMPLATE_SUBJECT, JOB_CREATION_TEMPLATE_HTML)
	_seed_template(
		FORWARDING_JOB_CREATION_TEMPLATE_NAME,
		FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
		FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	)

	if not frappe.db.get_single_value("FreightMas Settings", "default_job_creation_email_template"):
		frappe.db.set_single_value(
			"FreightMas Settings",
			"default_job_creation_email_template",
			JOB_CREATION_TEMPLATE_NAME,
		)
