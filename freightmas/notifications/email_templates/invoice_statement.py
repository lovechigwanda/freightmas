# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd
# For license information, please see license.txt

"""Invoice / statement of account email template body."""

INVOICE_STATEMENT_TEMPLATE_NAME = "Invoice Statement Notification"

INVOICE_STATEMENT_TEMPLATE_SUBJECT = "Invoice {{ invoice_name }} — Job {{ job_reference }}"

INVOICE_STATEMENT_TEMPLATE_HTML = """\
<p style="margin: 0 0 24px; font-size: 20px; font-weight: 700; line-height: 1.3; color: #0f172a;">Invoice {{ invoice_name }}</p>

<p style="margin: 0 0 24px;">Dear {{ customer_name or 'Sirs' }},</p>

<p style="margin: 0 0 24px;">Please find attached our invoice for services rendered on the shipment referenced below.</p>

<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 0 24px;">
<p style="margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: #64748b;">Invoice Summary</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; width: 100%; font-size: 13px;">
<tr><td style="padding: 2px 12px 2px 0; width: 130px; color: #64748b; vertical-align: top;">Invoice No.</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ invoice_name }}</td></tr>
{% if job_reference %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Job Reference</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ job_reference }}</td></tr>{% endif %}
{% if invoice_date %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Invoice Date</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ invoice_date }}</td></tr>{% endif %}
{% if payment_terms %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Terms</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ payment_terms }}</td></tr>{% endif %}
{% if due_date %}<tr><td style="padding: 2px 12px 2px 0; color: #64748b; vertical-align: top;">Due Date</td><td style="padding: 2px 0; font-weight: 600; color: #0f172a;">{{ due_date }}</td></tr>{% endif %}
</table>
{% if invoice_lines %}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 16px;">
{% for row in invoice_lines %}
<tr>
<td style="padding: 6px 0; color: #334155; border-bottom: 1px solid #e2e8f0;">{{ row.description }}</td>
<td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a; border-bottom: 1px solid #e2e8f0; white-space: nowrap;">{{ row.amount }}</td>
</tr>
{% endfor %}
<tr>
<td style="padding: 12px 0 0; font-weight: 700; color: #0f172a;">Total due ({{ currency or 'USD' }})</td>
<td style="padding: 12px 0 0; text-align: right; font-size: 16px; font-weight: 700; color: #0f172a; white-space: nowrap;">{{ grand_total }}</td>
</tr>
</table>
{% endif %}
</div>

<p style="margin: 0 0 24px;">Payment is due per the terms above. Please contact us if you require any clarification on this invoice, quoting Invoice <strong>{{ invoice_name }}</strong>.</p>

<div style="margin: 32px 0 0; padding-top: 16px; border-top: 1px solid #e2e8f0;">
<p style="margin: 0; color: #0f172a;">Yours faithfully,<br><strong>{{ company_name }}</strong></p>
</div>\
"""
