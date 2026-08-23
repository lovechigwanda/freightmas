# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Seed the modern Forwarding Job Creation Notification Email Template."""

from freightmas.patches.seed_job_creation_email_template import _seed_template
from freightmas.forwarding_service.notifications.job_creation_template_content import (
	FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	FORWARDING_JOB_CREATION_TEMPLATE_NAME,
	FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
)


def execute():
	_seed_template(
		FORWARDING_JOB_CREATION_TEMPLATE_NAME,
		FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT,
		FORWARDING_JOB_CREATION_TEMPLATE_HTML,
	)
