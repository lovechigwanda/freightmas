# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import requests
from frappe import _
from frappe.utils import cstr

from freightmas.integrations.resend.settings import get_api_key

RESEND_API_URL = "https://api.resend.com/emails"


class ResendAPIError(Exception):
	def __init__(self, status_code: int, message: str, response_body: str | None = None):
		super().__init__(message)
		self.status_code = status_code
		self.response_body = response_body


class ResendClient:
	def __init__(self, api_key: str | None = None):
		self.api_key = api_key or get_api_key()
		if not self.api_key:
			frappe.throw(_("Resend API key is not configured."))

	def send_email(self, payload: dict) -> dict:
		headers = {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
		}

		idempotency_key = payload.pop("idempotency_key", None)
		if idempotency_key:
			headers["Idempotency-Key"] = idempotency_key

		response = requests.post(
			RESEND_API_URL,
			headers=headers,
			data=json.dumps(payload),
			timeout=30,
		)

		if response.ok:
			return response.json()

		error_message = response.text
		try:
			error_data = response.json()
			error_message = error_data.get("message") or error_data.get("error") or response.text
		except Exception:
			pass

		raise ResendAPIError(response.status_code, cstr(error_message), response.text)
