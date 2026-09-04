# Client Portal notification helpers.

import frappe
from frappe.utils import get_fullname


def send_client_document_upload_email(job, document_label, file_name):
	"""Notify the job owner when a client uploads a document via the portal."""
	try:
		recipients = []
		if job.owner:
			recipients.append(job.owner)

		if not recipients:
			return

		responder = get_fullname(frappe.session.user)
		job_url = f"{frappe.utils.get_url()}/app/forwarding-job/{job.name}"
		subject = f"Shipment {job.name} - Client document uploaded"

		message = f"""
		<p>Dear {get_fullname(job.owner)},</p>

		<p>A client has uploaded a document for shipment <strong>{job.name}</strong>.</p>

		<table style="border-collapse: collapse; width: 100%; max-width: 600px;">
			<tr>
				<td style="padding: 8px; border: 1px solid #ddd;"><strong>Shipment</strong></td>
				<td style="padding: 8px; border: 1px solid #ddd;">{job.name}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border: 1px solid #ddd;"><strong>Document</strong></td>
				<td style="padding: 8px; border: 1px solid #ddd;">{document_label}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border: 1px solid #ddd;"><strong>File</strong></td>
				<td style="padding: 8px; border: 1px solid #ddd;">{file_name}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border: 1px solid #ddd;"><strong>Uploaded by</strong></td>
				<td style="padding: 8px; border: 1px solid #ddd;">{responder}</td>
			</tr>
		</table>

		<p style="margin-top: 20px;">
			<a href="{job_url}" style="background-color: #171717; color: white; padding: 10px 20px;
				text-decoration: none; border-radius: 4px; display: inline-block;">
				View Shipment
			</a>
		</p>
		"""

		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype="Forwarding Job",
			reference_name=job.name,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Client Portal Document Upload Email Error")
