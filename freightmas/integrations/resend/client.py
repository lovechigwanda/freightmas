# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import requests
from frappe import _
from frappe.utils import cstr, extract_email_id

from freightmas.integrations.resend.settings import get_api_key

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_DOMAINS_URL = "https://api.resend.com/domains"
VERIFIED_DOMAIN_STATUSES = frozenset({"verified", "partially_verified"})


class ResendAPIError(Exception):
	def __init__(self, status_code: int, message: str, response_body: str | None = None):
		super().__init__(message)
		self.status_code = status_code
		self.response_body = response_body


class ResendClient:
	def __init__(self, api_key: str | None = None):
		self.api_key = (api_key or get_api_key() or "").strip()
		if not self.api_key:
			frappe.throw(_("Resend API key is not configured."))

	def _request(self, method: str, url: str) -> requests.Response:
		return requests.request(
			method,
			url,
			headers={"Authorization": f"Bearer {self.api_key}"},
			timeout=30,
		)

	def list_domains(self) -> list[dict]:
		response = self._request("GET", RESEND_DOMAINS_URL)
		if not response.ok:
			error_message = response.text
			try:
				error_data = response.json()
				error_message = error_data.get("message") or error_data.get("error") or response.text
			except Exception:
				pass
			raise ResendAPIError(response.status_code, cstr(error_message), response.text)

		payload = response.json()
		return payload.get("data") or []

	def get_domain_status_map(self) -> dict[str, str]:
		return {
			(row.get("name") or "").lower(): row.get("status") or "unknown"
			for row in self.list_domains()
			if row.get("name")
		}

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
