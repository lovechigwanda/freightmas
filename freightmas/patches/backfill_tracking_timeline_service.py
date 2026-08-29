"""Backfill service field on existing Forwarding Tracking Event rows."""

import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabForwarding Tracking Event`
		SET service = 'Sea / Air Freight'
		WHERE source = 'API' AND IFNULL(service, '') = ''
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabForwarding Tracking Event`
		SET service = 'General'
		WHERE IFNULL(source, '') != 'API' AND IFNULL(service, '') = ''
		"""
	)
	frappe.db.commit()
