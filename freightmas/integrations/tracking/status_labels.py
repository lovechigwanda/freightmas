# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Standardized wording for Searates tracking milestones.

Carriers describe the same DCSA event differently ("Vessel Discharge" vs
"DISCHARGED FROM VESSEL" vs ...). Searates events carry a structured
event_code alongside the carrier's free-text description; this module maps
that code to one fixed, human-readable phrase so tracking comments read the
same regardless of carrier.
"""

import frappe

# DCSA event code -> standardized milestone phrase.
# Codes already load-bearing in searates.py's date-matching logic (see the
# comment block above _apply_event_date there) are seeded here; extend this
# table as new codes are observed (see _log_unmapped_code below).
EVENT_CODE_LABELS = {
	"CONF": "Booking confirmed",
	"RECE": "Cargo received",
	"GTIN": "Gated in at terminal",
	"LOAD": "Loaded on vessel",
	"DEPA": "Vessel departed",
	"ARRI": "Vessel arrived",
	"DISC": "Vessel discharged",
	"GTOT": "Gated out to consignee",
	"GOUT": "Gated out",
	"AVPU": "Available for pickup",
	"DLVR": "Delivered to consignee",
	"IRTN": "Empty container returned",
	"EMRT": "Empty container returned",
	"RTRN": "Empty container returned",
	"STUF": "Container stuffed",
	"STRP": "Container stripped",
}


def standardized_event_label(event_code, description):
	"""Map a DCSA event code to fixed wording; fall back to the carrier's own
	description (capitalized) for codes not yet in the table."""
	label = EVENT_CODE_LABELS.get(event_code)
	if label:
		return label
	if event_code:
		_log_unmapped_code(event_code, description)
	return (description or "").strip().capitalize()


def build_tracking_comment(status_label, event_code, description, date_str):
	"""'{status} - {standardized milestone}: {date}' — the one place this
	comment string is assembled for both Forwarding Job and Clearing Job."""
	event_label = standardized_event_label(event_code, description)
	parts = [p for p in [status_label, event_label] if p]
	comment = " - ".join(parts)
	if date_str:
		comment = f"{comment}: {date_str}"
	return comment


def _log_unmapped_code(event_code, description):
	frappe.logger().info(f"Unmapped Searates event_code {event_code!r}: {description!r}")
