# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address

from freightmas.integrations.resend.defaults import (
	get_default_allowed_domains_text,
	get_default_fallback_sender,
	get_sender_display_name,
	get_site_sending_domain,
)
from freightmas.integrations.resend.settings import get_stored_api_key


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

		self._validate_resend_api_key()

		if self.enabled and not get_stored_api_key():
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

	def _validate_resend_api_key(self):
		pwd = self.get("resend_api_key")
		if not pwd or self.is_dummy_password(pwd):
			return

		pwd = pwd.strip()
		if pwd.startswith("re_"):
			return

		# Prevent unrelated values (e.g. Frappe User REST api_key hashes) overwriting the secret.
		self.flags.ignore_save_passwords = ["resend_api_key"]
		stored = get_stored_api_key()
		if stored:
			self.resend_api_key = "*" * len(stored)
		else:
			self.resend_api_key = None

		frappe.throw(
			_(
				"Invalid Resend API key. Keys from resend.com start with <code>re_</code>. "
				"Paste your Resend sending key and save again."
			),
			title=_("Resend API Key"),
		)


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
def check_resend_domains():
	frappe.only_for(("System Manager", "FreightMas Admin"))

	from freightmas.integrations.resend.client import ResendAPIError, ResendClient
	from freightmas.integrations.resend.settings import get_stored_api_key

	api_key = get_stored_api_key()
	if not api_key:
		frappe.throw(_("Save a Resend API Key first."))

	try:
		domains = ResendClient(api_key=api_key).list_domains()
	except ResendAPIError as exc:
		frappe.throw(_("Could not list Resend domains ({0}): {1}").format(exc.status_code, exc))

	return {
		"domains": [
			{
				"name": row.get("name"),
				"status": row.get("status"),
				"region": row.get("region"),
			}
			for row in domains
		]
	}


@frappe.whitelist()
def send_test_email(recipient=None):
	frappe.only_for(("System Manager", "FreightMas Admin"))

	from freightmas.integrations.resend.client import ResendAPIError, ResendClient
	from freightmas.integrations.resend.settings import get_stored_api_key
	from freightmas.integrations.resend.validation import (
		format_resend_error,
		resolve_test_sender,
		validate_sender_for_resend,
	)

	settings = frappe.get_single("Resend Settings")
	api_key = get_stored_api_key()
	if not api_key:
		frappe.throw(
			_("Save a valid Resend API Key before sending a test email. Create one at resend.com/api-keys.")
		)

	if not settings.fallback_sender:
		frappe.throw(
			_("Set Fallback Sender to an address on your verified Resend domain before sending a test email.")
		)

	recipient = recipient or settings.test_recipient or frappe.db.get_value("User", frappe.session.user, "email")
	if not recipient:
		frappe.throw(_("No test recipient email address found."))

	validate_email_address(recipient, throw=True)

	sender = resolve_test_sender(settings)
	validate_sender_for_resend(api_key, sender)

	try:
		ResendClient(api_key=api_key).send_email(
			{
				"from": sender,
				"to": [recipient],
				"subject": _("{0} Resend test email").format(get_sender_display_name()),
				"html": (
					f"<p>{_('This is a test email sent via Resend.')}</p>"
					f"<p>{_('From')}: {frappe.utils.escape_html(sender)}</p>"
				),
				"text": _("This is a test email sent via Resend. From: {0}").format(sender),
			}
		)
	except ResendAPIError as exc:
		frappe.throw(format_resend_error(exc, sender, recipient), title=_("Resend Error"))

	return {
		"success": True,
		"message": _("Test email sent to {0} from {1}").format(recipient, sender),
	}
