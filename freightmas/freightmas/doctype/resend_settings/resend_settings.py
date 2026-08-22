# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_formatted_email, validate_email_address

from freightmas.integrations.resend.defaults import (
	get_default_allowed_domains_text,
	get_default_fallback_sender,
	get_sender_display_name,
	get_site_sending_domain,
)


class ResendSettings(Document):
	def validate(self):
		if not self.allowed_domains:
			suggested = get_default_allowed_domains_text()
			if suggested:
				self.allowed_domains = suggested

		if not self.fallback_sender:
			suggested = get_default_fallback_sender()
			if suggested:
				self.fallback_sender = suggested

		if self.fallback_sender:
			validate_email_address(self.fallback_sender, throw=True)

		if self.test_recipient:
			validate_email_address(self.test_recipient, throw=True)

		if self.enabled and not self.get_password("api_key"):
			frappe.throw(_("Resend API Key is required when Resend is enabled."))

		if self.enabled and not get_allowed_domains_from_doc(self):
			frappe.throw(
				_(
					"Set Allowed Domains before enabling Resend. "
					"Add your verified Resend domain(s), one per line."
				)
			)

		if self.enabled and not self.fallback_sender:
			frappe.throw(_("Set Fallback Sender before enabling Resend."))


def get_allowed_domains_from_doc(doc) -> list[str]:
	raw = (doc.allowed_domains or "").strip()
	return [domain.strip().lower() for domain in raw.splitlines() if domain.strip()]


@frappe.whitelist()
def get_setup_context():
	domain = get_site_sending_domain()
	app_name = get_sender_display_name()
	suggested_fallback = get_default_fallback_sender()

	instructions = f"""
<ol>
<li>Verify your sending domain in the <a href="https://resend.com/domains" target="_blank">Resend dashboard</a> (SPF, DKIM, DMARC DNS records).</li>
<li>Create a <strong>Sending API key</strong> in Resend and paste it below.</li>
<li>Set the fallback sender (used for system emails such as password resets).</li>
<li>Add allowed sender domain(s), one per line.</li>
<li>Enable Resend and send a test email.</li>
</ol>
"""

	if domain:
		instructions += f"""
<p><strong>Suggested domain for this site:</strong> {domain}<br>
<strong>Suggested sender name:</strong> {frappe.utils.escape_html(app_name)}<br>
<strong>Suggested fallback sender:</strong> {frappe.utils.escape_html(suggested_fallback or "")}</p>
"""
	else:
		instructions += """
<p><strong>No sending domain detected.</strong> Set a company email or default outgoing Email Account, then reload this form to see suggestions.</p>
"""

	return {
		"suggested_domain": domain,
		"suggested_fallback_sender": suggested_fallback,
		"suggested_allowed_domains": get_default_allowed_domains_text(),
		"setup_instructions_html": instructions,
	}


@frappe.whitelist()
def send_test_email(recipient=None):
	frappe.only_for(("System Manager", "FreightMas Admin"))

	settings = frappe.get_single("Resend Settings")
	if not settings.get_password("api_key"):
		frappe.throw(_("Set a Resend API Key before sending a test email."))

	recipient = recipient or settings.test_recipient or frappe.db.get_value("User", frappe.session.user, "email")
	if not recipient:
		frappe.throw(_("No test recipient email address found."))

	validate_email_address(recipient, throw=True)

	sender = get_formatted_email(frappe.session.user)
	if not sender:
		from freightmas.integrations.resend.settings import get_fallback_sender

		sender = get_fallback_sender()

	from freightmas.integrations.resend.client import ResendClient

	client = ResendClient()
	client.send_email(
		{
			"from": sender,
			"to": [recipient],
			"subject": _("{0} Resend test email").format(get_sender_display_name()),
			"html": f"<p>{_('This is a test email sent via Resend.')}</p>",
			"text": _("This is a test email sent via Resend."),
		}
	)

	return {"success": True, "message": _("Test email sent to {0}").format(recipient)}
