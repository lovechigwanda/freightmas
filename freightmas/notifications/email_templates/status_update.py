# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Shipment status update email template body."""

STATUS_UPDATE_TEMPLATE_NAME = "Shipment Status Update"

STATUS_UPDATE_TEMPLATE_SUBJECT = "Status update — Job: {{ name }} {{ customer_name }}"

STATUS_UPDATE_TEMPLATE_HTML = """\
<p style="margin: 0 0 24px; font-size: 20px; font-weight: 700; line-height: 1.3; color: #0f172a;">Status update — Job {{ name }}</p>

<p style="margin: 0 0 24px;">Dear {{ customer_name }},</p>

<p style="margin: 0 0 24px;">Please note the following update on your shipment.</p>

<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 24px;">
<p style="margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #64748b;">Current Status</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; width: 100%; font-size: 13px;">
<tr><td style="padding: 2px 12px 2px 0; width: 130px; color: #64748b; vertical-align: top;">Job Reference</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ name }}</td></tr>
{% if status_label %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Milestone</td><td style="padding: 2px 0; font-weight: 600; color: #16a34a;">{{ status_label }}</td></tr>{% endif %}
{% if status_datetime %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Date / Time</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ status_datetime }}</td></tr>{% endif %}
{% if current_location %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Location</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ current_location }}</td></tr>{% endif %}
{% if container_list %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Container(s)</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ container_list }}</td></tr>{% endif %}
{% if next_step %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Next step</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ next_step }}</td></tr>{% endif %}
{% if eta_formatted %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">ETA</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ eta_formatted }}</td></tr>{% endif %}
</table>
</div>

{% if next_step %}
<p style="margin: 0 0 24px;">Our team will proceed with <strong>{{ next_step }}</strong>. Kindly quote Job Reference <strong>{{ name }}</strong> in any correspondence.</p>
{% else %}
<p style="margin: 0 0 24px;">Kindly quote Job Reference <strong>{{ name }}</strong> in any correspondence regarding this shipment.</p>
{% endif %}

<div style="margin: 32px 0 0; padding-top: 16px; border-top: 1px solid #e2e8f0;">
<p style="margin: 0; color: #0f172a;">Yours faithfully,<br><strong>{{ company_name }}</strong></p>
</div>\
"""
