# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Documentation request email template body."""

DOCUMENTATION_REQUEST_TEMPLATE_NAME = "Documentation Request"

DOCUMENTATION_REQUEST_TEMPLATE_SUBJECT = (
	"Documents outstanding — Job: {{ name }} {{ customer_name }}"
)

DOCUMENTATION_REQUEST_TEMPLATE_HTML = """\
<p style="margin: 0 0 24px; font-size: 20px; font-weight: 700; line-height: 1.3; color: #0f172a;">Documents outstanding — Job {{ name }}</p>

<p style="margin: 0 0 24px;">Dear {{ customer_name }},</p>

<p style="margin: 0 0 24px;">We are preparing the customs entry for this shipment and require the following documents to proceed without delay.</p>

{% if missing_docs %}
<div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 14px 16px; margin: 0 0 24px;">
<p style="margin: 0 0 8px; font-size: 13px; font-weight: 600; color: #92400e;">Action required — documents outstanding</p>
<p style="margin: 0 0 8px; font-size: 13px; color: #78350f;">Please provide the following at your earliest convenience:</p>
<ul style="margin: 0 0 8px; padding-left: 18px; font-size: 13px; color: #78350f;">
{% for doc_label in missing_docs %}<li style="margin: 0 0 4px;">{{ doc_label }}</li>{% endfor %}
</ul>
<p style="margin: 0; font-size: 13px; color: #78350f;">Delays in receiving these documents may result in storage or demurrage charges.</p>
</div>
{% endif %}

<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 24px;">
<p style="margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #64748b;">Shipment Reference</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; width: 100%; font-size: 13px;">
<tr><td style="padding: 2px 12px 2px 0; width: 130px; color: #64748b; vertical-align: top;">Job Reference</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ name }}</td></tr>
<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">BL Number</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ bl_number_display }}</td></tr>
{% if vessel_eta %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Vessel / ETA</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ vessel_eta }}</td></tr>{% endif %}
{% if free_time_ends %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Free time ends</td><td style="padding: 2px 0; font-weight: 600; color: #b45309;">{{ free_time_ends }}</td></tr>{% endif %}
</table>
</div>

<p style="margin: 0 0 24px;">Please reply with the requested documents, quoting Job Reference <strong>{{ name }}</strong>.</p>

<div style="margin: 32px 0 0; padding-top: 16px; border-top: 1px solid #e2e8f0;">
<p style="margin: 0; color: #0f172a;">Yours faithfully,<br><strong>{{ company_name }}</strong></p>
</div>\
"""
