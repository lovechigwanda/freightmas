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

# DCSA event code -> (confirmed phrase, expected phrase). Searates mixes
# confirmed and forward-looking/projected events in the same events[] array,
# distinguished only by the event's own "actual" flag (see searates.py's
# _apply_event_date, which already relies on this same flag) — a projected
# event must read in future tense, not as something that already happened.
# Codes already load-bearing in searates.py's date-matching logic (see the
# comment block above _apply_event_date there) are seeded here; extend this
# table as new codes are observed (see _log_unmapped_code below).
EVENT_CODE_LABELS = {
	"CONF": ("Booking confirmed", "Booking confirmation expected"),
	"RECE": ("Cargo received", "Cargo receipt expected"),
	"GTIN": ("Gated in at terminal", "Gate-in at terminal expected"),
	"LOAD": ("Loaded on vessel", "Loading on vessel expected"),
	"DEPA": ("Vessel departed", "Vessel departure expected"),
	"ARRI": ("Vessel arrived", "Vessel arrival expected"),
	"DISC": ("Vessel discharged", "Vessel discharge expected"),
	"GTOT": ("Gated out to consignee", "Gate-out to consignee expected"),
	"GOUT": ("Gated out", "Gate-out expected"),
	"AVPU": ("Available for pickup", "Availability for pickup expected"),
	"DLVR": ("Delivered to consignee", "Delivery to consignee expected"),
	"IRTN": ("Empty container returned", "Empty container return expected"),
	"EMRT": ("Empty container returned", "Empty container return expected"),
	"RTRN": ("Empty container returned", "Empty container return expected"),
	"STUF": ("Container stuffed", "Container stuffing expected"),
	"STRP": ("Container stripped", "Container stripping expected"),
}


def standardized_event_label(event_code, description, actual=True):
	"""Map a DCSA event code to fixed wording, in the tense matching whether
	the event is confirmed or still projected; fall back to the carrier's own
	description (capitalized, flagged "(expected)" if projected) for codes
	not yet in the table."""
	labels = EVENT_CODE_LABELS.get(event_code)
	if labels:
		return labels[0] if actual else labels[1]
	if event_code:
		_log_unmapped_code(event_code, description)
	text = (description or "").strip().capitalize()
	if text and not actual:
		text = f"{text} (expected)"
	return text


def build_tracking_comment(status_label, event_code, description, date_str, actual=True):
	"""'{status} - {standardized milestone}: {date}' — the one place this
	comment string is assembled for both Forwarding Job and Clearing Job."""
	event_label = standardized_event_label(event_code, description, actual)
	parts = [p for p in [status_label, event_label] if p]
	comment = " - ".join(parts)
	if date_str:
		comment = f"{comment}: {date_str}"
	return comment


def _log_unmapped_code(event_code, description):
	frappe.logger().info(f"Unmapped Searates event_code {event_code!r}: {description!r}")
