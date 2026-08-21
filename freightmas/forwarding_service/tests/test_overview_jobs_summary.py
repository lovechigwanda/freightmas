import unittest

from freightmas.freightmas.page.shipment_dashboard.shipment_dashboard import (
	NOT_ACTIVE_STATUSES,
	_build_jobs_summary,
)


class TestOverviewJobsSummary(unittest.TestCase):
	def test_build_jobs_summary_shape(self):
		result = _build_jobs_summary(active_only=False)
		self.assertIn("by_status", result)
		self.assertIn("containers", result)
		self.assertIn("parcels", result)
		self.assertIn("by_direction", result)
		self.assertIsInstance(result["containers"], int)
		self.assertIsInstance(result["parcels"], int)

	def test_active_summary_excludes_inactive_statuses(self):
		all_summary = _build_jobs_summary(active_only=False)
		active_summary = _build_jobs_summary(active_only=True)

		all_total = sum(row.count for row in all_summary["by_status"])
		active_total = sum(row.count for row in active_summary["by_status"])
		self.assertLessEqual(active_total, all_total)

		active_statuses = {row.status for row in active_summary["by_status"]}
		for status in NOT_ACTIVE_STATUSES:
			self.assertNotIn(status, active_statuses)

	def test_direction_rows_include_cargo_counts(self):
		result = _build_jobs_summary(active_only=False)
		for row in result["by_direction"]:
			self.assertIn("direction", row)
			self.assertIn("jobs", row)
			self.assertIn("containers", row)
			self.assertIn("parcels", row)


if __name__ == "__main__":
	unittest.main()
