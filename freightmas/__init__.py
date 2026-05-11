__version__ = "0.0.1"


def _patch_file_lock():
	"""Defensive fix for Frappe TOCTOU race in file_lock.lock_age.
	If the lock file disappears between is_locked() and check_if_locked(),
	treat the age as infinite (= expired = not locked)."""
	from pathlib import Path
	from time import time

	import frappe.utils.file_lock as _fl

	def _safe_lock_age(name: str) -> float:
		try:
			return time() - Path(_fl.get_lock_path(name)).stat().st_mtime
		except FileNotFoundError:
			return float("inf")

	_fl.lock_age = _safe_lock_age


_patch_file_lock()
