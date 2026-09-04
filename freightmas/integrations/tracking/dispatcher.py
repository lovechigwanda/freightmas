# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Route tracking requests to the configured provider."""

import frappe

from freightmas.integrations.tracking.base import get_tracking_provider, resolve_sealine_for_traqo


def fetch_tracking(number, tracking_type="BL", sealine=None, shipping_line=None, traqo_shipment_id=None):
	"""Fetch tracking data from the configured provider."""
	provider = get_tracking_provider()
	sealine = resolve_sealine_for_traqo(number, tracking_type, sealine, shipping_line)

	if provider == "Traqo":
		from freightmas.integrations.tracking.traqo import fetch_tracking as traqo_fetch
		return traqo_fetch(
			number,
			tracking_type=tracking_type,
			sealine=sealine,
			traqo_shipment_id=traqo_shipment_id,
		)

	from freightmas.integrations.tracking.searates import fetch_tracking as searates_fetch
	return searates_fetch(number, tracking_type=tracking_type, sealine=sealine)


def refresh_tracking(number, tracking_type="BL", sealine=None, shipping_line=None, traqo_shipment_id=None):
	"""Refresh tracking for scheduler/webhook use."""
	provider = get_tracking_provider()
	sealine = resolve_sealine_for_traqo(number, tracking_type, sealine, shipping_line)

	if provider == "Traqo":
		from freightmas.integrations.tracking.traqo import refresh_tracking as traqo_refresh
		return traqo_refresh(
			traqo_shipment_id,
			number,
			tracking_type=tracking_type,
			sealine=sealine,
		)

	return fetch_tracking(number, tracking_type=tracking_type, sealine=sealine, shipping_line=shipping_line)


def untrack_shipment(traqo_shipment_id):
	if get_tracking_provider() != "Traqo":
		return False

	from freightmas.integrations.tracking.traqo import untrack_shipment as traqo_untrack
	return traqo_untrack(traqo_shipment_id)


def list_updated_reference_numbers(updated_since):
	if get_tracking_provider() != "Traqo":
		return None

	from freightmas.integrations.tracking.traqo import list_updated_shipments
	return list_updated_shipments(updated_since)
