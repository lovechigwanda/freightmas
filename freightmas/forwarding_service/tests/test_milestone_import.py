# Copyright (c) 2026, Zvomaita Technologies (Pvt) Ltd and contributors
# For license information, please see license.txt

"""Unit tests for the milestone import engine, focused on the Port Clearance
tracking-comment column and the submitted-job skip. The DB seams
(`frappe.db.exists`, `frappe.get_doc`, `frappe.has_permission`) are patched so
these stay fast and fixture-free, mirroring test_operational_phase.py."""

import unittest
from unittest import mock

import frappe

from freightmas.forwarding_service import milestone_import as mi


def _row(**kwargs):
	base = {
		"name": "row-1",
		"milestone_code": "PC_PREALERT_RECEIVED",
		"milestone_label": "Pre-Alert Received",
		"is_completed": 0,
		"completed_on": None,
		"remarks": None,
	}
	base.update(kwargs)
	return frappe._dict(base)


class _FakeJob:
	def __init__(self, docstatus=0, tables=None, values=None):
		self.docstatus = docstatus
		self._tables = tables or {}
		self._values = values or {}
		self.saved = False

	def get(self, field, default=None):
		if field in self._tables:
			return self._tables[field]
		return self._values.get(field, default)

	def set(self, field, value):
		self._values[field] = value

	def save(self):
		self.saved = True


def _column_map():
	return {
		"pre-alert received": {
			"milestone": "MD-PC-1",
			"milestone_code": "PC_PREALERT_RECEIVED",
			"milestone_label": "Pre-Alert Received",
			"service_module": "Port Clearance",
		}
	}


def _patch_jobs(jobs):
	"""Patch the DB seams so classify_rows/apply_updates resolve `jobs`
	(a {name: _FakeJob} registry) without a real site."""
	return mock.patch.multiple(
		frappe,
		get_doc=mock.Mock(side_effect=lambda dt, name: jobs[name]),
		has_permission=mock.Mock(return_value=True),
	), mock.patch.object(frappe.db, "exists", side_effect=lambda dt, name: name in jobs)


class TestMilestoneImportClassify(unittest.TestCase):
	HEADERS = ["Job Reference", "Pre-Alert Received", "Tracking Comment"]

	def _classify(self, data_rows, jobs):
		p_frappe, p_exists = _patch_jobs(jobs)
		with p_frappe, p_exists:
			return mi.classify_rows(
				self.HEADERS, data_rows, "job reference", _column_map(), "Port Clearance"
			)

	def test_comment_column_captured_and_excluded_from_unmapped(self):
		jobs = {
			"JOB-1": _FakeJob(
				tables={"port_clearance_milestones": [_row()]},
				values={"port_clearance_tracking_comment": "old"},
			)
		}
		result = self._classify(
			[["JOB-1", "2026-02-01", "At port, awaiting release"]], jobs
		)

		# Milestone still classified normally.
		self.assertEqual(len(result["to_update"]), 1)
		# Tracking Comment is not an unmapped column.
		self.assertEqual(result["unmapped_columns"], [])
		# Comment captured with existing value and override text.
		self.assertEqual(len(result["comment_updates"]), 1)
		entry = result["comment_updates"][0]
		self.assertEqual(entry["job"], "JOB-1")
		self.assertEqual(entry["fieldname"], "port_clearance_tracking_comment")
		self.assertEqual(entry["comment"], "At port, awaiting release")
		self.assertEqual(entry["existing_comment"], "old")

	def test_empty_comment_cell_is_skipped(self):
		jobs = {
			"JOB-3": _FakeJob(
				tables={"port_clearance_milestones": [_row(name="row-3")]},
				values={"port_clearance_tracking_comment": "keep me"},
			)
		}
		result = self._classify([["JOB-3", "2026-02-02", ""]], jobs)

		self.assertEqual(result["comment_updates"], [])
		# Milestone work is unaffected by the blank comment.
		self.assertEqual(len(result["to_update"]), 1)

	def test_submitted_job_is_skipped_entirely(self):
		jobs = {
			"JOB-2": _FakeJob(
				docstatus=1,
				tables={"port_clearance_milestones": [_row(name="row-2")]},
				values={"port_clearance_tracking_comment": "old"},
			)
		}
		result = self._classify([["JOB-2", "2026-02-05", "Should be ignored"]], jobs)

		self.assertEqual(result["submitted_jobs"], ["JOB-2"])
		self.assertEqual(result["to_update"], [])
		self.assertEqual(result["comment_updates"], [])

	def test_comment_column_ignored_for_module_without_field(self):
		# Border Clearance has no tracking-comment field configured, so the
		# "Tracking Comment" header falls through to unmapped_columns.
		jobs = {
			"JOB-9": _FakeJob(tables={"border_clearance_milestones": [_row(name="row-9")]})
		}
		column_map = {
			"pre-alert received": {
				"milestone": "MD-BC-1",
				"milestone_code": "PC_PREALERT_RECEIVED",
				"milestone_label": "Pre-Alert Received",
				"service_module": "Border Clearance",
			}
		}
		p_frappe, p_exists = _patch_jobs(jobs)
		with p_frappe, p_exists:
			result = mi.classify_rows(
				self.HEADERS, [["JOB-9", "2026-02-01", "x"]], "job reference", column_map, "Border Clearance"
			)
		self.assertIn("Tracking Comment", result["unmapped_columns"])
		self.assertEqual(result["comment_updates"], [])


class TestMilestoneImportApply(unittest.TestCase):
	def _apply(self, updates, comment_updates, jobs):
		p_frappe, p_exists = _patch_jobs(jobs)
		with p_frappe, p_exists:
			return mi.apply_updates(updates, comment_updates)

	def test_comment_overrides_and_milestone_applied(self):
		job = _FakeJob(
			tables={"port_clearance_milestones": [_row()]},
			values={"port_clearance_tracking_comment": "old"},
		)
		summary = self._apply(
			[{
				"job": "JOB-1",
				"fieldname": "port_clearance_milestones",
				"row_name": "row-1",
				"milestone_code": "PC_PREALERT_RECEIVED",
				"milestone_label": "Pre-Alert Received",
				"completed_on": "2026-02-01",
			}],
			[{
				"job": "JOB-1",
				"fieldname": "port_clearance_tracking_comment",
				"service_module": "Port Clearance",
				"comment": "At port",
				"existing_comment": "old",
			}],
			{"JOB-1": job},
		)

		self.assertTrue(job.saved)
		self.assertEqual(job.get("port_clearance_tracking_comment"), "At port")
		self.assertEqual(job.get("port_clearance_milestones")[0].is_completed, 1)
		self.assertEqual(summary["updated_count"], 2)
		self.assertEqual(summary["failed_count"], 0)

	def test_comment_only_run_saves_job(self):
		job = _FakeJob(values={"port_clearance_tracking_comment": "old"})
		summary = self._apply(
			[],
			[{
				"job": "JOB-1",
				"fieldname": "port_clearance_tracking_comment",
				"service_module": "Port Clearance",
				"comment": "New status",
				"existing_comment": "old",
			}],
			{"JOB-1": job},
		)
		self.assertTrue(job.saved)
		self.assertEqual(job.get("port_clearance_tracking_comment"), "New status")
		self.assertEqual(summary["updated_count"], 1)

	def test_submitted_job_guard_skips_without_saving(self):
		job = _FakeJob(docstatus=1, values={"port_clearance_tracking_comment": "old"})
		summary = self._apply(
			[],
			[{
				"job": "JOB-1",
				"fieldname": "port_clearance_tracking_comment",
				"service_module": "Port Clearance",
				"comment": "New status",
				"existing_comment": "old",
			}],
			{"JOB-1": job},
		)
		self.assertFalse(job.saved)
		self.assertEqual(job.get("port_clearance_tracking_comment"), "old")
		self.assertEqual(summary["skipped_count"], 1)
		self.assertEqual(summary["updated_count"], 0)
