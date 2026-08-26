# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Default Email Template content for job creation notifications."""

JOB_CREATION_TEMPLATE_NAME = "Job Creation Notification"

JOB_CREATION_TEMPLATE_SUBJECT = (
	"New Shipment - Job: {{ name }} {{ customer_name }} {{ customer_reference }}"
)

JOB_CREATION_TEMPLATE_HTML = """\
<p style="margin: 0 0 16px;">Dear {{ customer_name }},</p>

<p style="margin: 0 0 16px;">Your shipment has been registered in our system with the following details:</p>

<table style="border-collapse: collapse; margin: 0 0 16px;">
<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Job Reference:</td><td style="padding: 4px 0;">{{ name }}</td></tr>
<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">BL Number:</td><td style="padding: 4px 0;">{{ bl_number_display }}</td></tr>
{% if direction %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Direction:</td><td style="padding: 4px 0;">{{ direction }}</td></tr>{% endif %}
{% if shipment_mode %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Mode:</td><td style="padding: 4px 0;">{{ shipment_mode }}</td></tr>{% endif %}
{% if shipment_type %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Shipment Type:</td><td style="padding: 4px 0;">{{ shipment_type }}</td></tr>{% endif %}
{% if route %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Route:</td><td style="padding: 4px 0;">{{ route }}</td></tr>{% endif %}
{% if eta_formatted %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">ETA:</td><td style="padding: 4px 0;">{{ eta_formatted }}</td></tr>{% endif %}
{% if cargo_summary %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Cargo:</td><td style="padding: 4px 0;">{{ cargo_summary }}</td></tr>{% endif %}
{% if consignee_name %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Consignee:</td><td style="padding: 4px 0;">{{ consignee_name }}</td></tr>{% endif %}
{% if services_enabled %}<tr><td style="padding: 4px 24px 4px 0; font-weight: 600;">Services:</td><td style="padding: 4px 0;">{{ services_enabled }}</td></tr>{% endif %}
</table>

<p style="margin: 0 0 16px;">Please quote the Job Reference <strong>{{ name }}</strong> in all future correspondence regarding this shipment.</p>

{% if missing_docs %}
<div style="background: #FAEEDA; border-radius: 8px; padding: 12px 16px; margin: 0 0 16px;">
<p style="margin: 0 0 8px; font-weight: 600; color: #854F0B;">Action required — documents outstanding</p>
<p style="margin: 0 0 8px;">The following documents are still needed to clear this shipment through port:</p>
<ul style="margin: 0 0 8px; padding-left: 20px;">
{% for doc_label in missing_docs %}<li>{{ doc_label }}</li>{% endfor %}
</ul>
<p style="margin: 0;">Please send these at your earliest convenience to avoid delaying the shipment.</p>
</div>
{% endif %}

<p style="margin: 0 0 16px;">If you have any questions, feel free to reach out — we're happy to help.</p>
<p style="margin: 0 0 16px;">Thank you for your business.</p>
<p style="margin: 0;">Best regards,<br>{{ company_name }}</p>\
"""

FORWARDING_JOB_CREATION_TEMPLATE_NAME = "Forwarding Job Creation Notification"

FORWARDING_JOB_CREATION_TEMPLATE_SUBJECT = JOB_CREATION_TEMPLATE_SUBJECT

FORWARDING_JOB_CREATION_TEMPLATE_HTML = """\
<div style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.5; color: #334155; max-width: 600px;">

<p style="margin: 0 0 24px;">Dear {{ customer_name }},</p>

<p style="margin: 0 0 20px;">Your shipment has been registered in our system. A summary of the key details is below.</p>

<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 24px;">
<p style="margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #64748b;">Shipment Details</p>
<table style="border-collapse: collapse; width: 100%; font-size: 13px;">
<tr><td style="padding: 2px 12px 2px 0; width: 130px; color: #64748b; vertical-align: top;">Job Reference</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ name }}</td></tr>
<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">BL Number</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ bl_number_display }}</td></tr>
{% if direction %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Direction</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ direction }}</td></tr>{% endif %}
{% if shipment_mode %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Mode</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ shipment_mode }}</td></tr>{% endif %}
{% if shipment_type %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Shipment Type</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ shipment_type }}</td></tr>{% endif %}
{% if route %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Route</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ route }}</td></tr>{% endif %}
{% if eta_formatted %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">ETA</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ eta_formatted }}</td></tr>{% endif %}
{% if cargo_summary %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Cargo</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ cargo_summary }}</td></tr>{% endif %}
{% if consignee_name %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Consignee</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ consignee_name }}</td></tr>{% endif %}
{% if services_enabled %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Services</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ services_enabled }}</td></tr>{% endif %}
</table>
</div>

<p style="margin: 0 0 24px;">Please quote the Job Reference <strong>{{ name }}</strong> in all future correspondence regarding this shipment.</p>

{% if missing_docs %}
<div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 14px 16px; margin: 0 0 24px;">
<p style="margin: 0 0 8px; font-size: 13px; font-weight: 600; color: #92400e;">Action required — documents outstanding</p>
<p style="margin: 0 0 8px; font-size: 13px; color: #78350f;">The following documents are still needed to clear this shipment through port:</p>
<ul style="margin: 0 0 8px; padding-left: 18px; font-size: 13px; color: #78350f;">
{% for doc_label in missing_docs %}<li style="margin: 0 0 4px;">{{ doc_label }}</li>{% endfor %}
</ul>
<p style="margin: 0; font-size: 13px; color: #78350f;">Please send these at your earliest convenience to avoid delaying the shipment.</p>
</div>
{% endif %}

<p style="margin: 0 0 24px;">If you have any questions, feel free to reach out — we're happy to help.</p>

<p style="margin: 0 0 24px;">Thank you for your business.</p>

<div style="margin: 32px 0 0; padding-top: 16px; border-top: 1px solid #e2e8f0;">
<p style="margin: 0; color: #0f172a;">Best regards,<br><strong>{{ company_name }}</strong></p>
</div>

</div>\
"""
