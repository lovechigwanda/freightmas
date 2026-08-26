# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Remove branded email layout templates and restore job creation templates."""

import frappe

from freightmas.forwarding_service.notifications.job_creation_template_content import (
	FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	FORWARDING_JOB_CREATION_TEMPLATE_NAME,
	FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
	JOB_CREATION_TEMPLATE_HTML,
	JOB_CREATION_TEMPLATE_NAME,
	JOB_CREATION_TEMPLATE_SUBJECT,
)

# Templates introduced by the reverted branded email layout work.
_TEMPLATES_TO_DELETE = (
	"Shipment Status Update",
	"Documentation Request",
	"Invoice Statement Notification",
)

_TEMPLATES_TO_RESTORE = (
	(JOB_CREATION_TEMPLATE_NAME, JOB_CREATION_TEMPLATE_SUBJECT, JOB_CREATION_TEMPLATE_HTML),
	(
		FORWARDING_JOB_CREATION_TEMPLATE_NAME,
		FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
		FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	),
)


def execute():
	for name in _TEMPLATES_TO_DELETE:
		if frappe.db.exists("Email Template", name):
			frappe.delete_doc("Email Template", name, force=1, ignore_permissions=True)

	for name, subject, response_html in _TEMPLATES_TO_RESTORE:
		if not frappe.db.exists("Email Template", name):
			continue
		frappe.db.set_value(
			"Email Template",
			name,
			{"subject": subject, "use_html": 1, "response_html": response_html},
			update_modified=True,
		)
