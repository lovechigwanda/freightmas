# File-attachment privacy enforcement for job/invoice documents.
#
# The Client Portal never serves a raw /private/files/<name> URL (see
# freightmas/portal/api/documents.py, Phase 2) — but that guarantee only
# holds if every File attached to a job or invoice is actually private.
# This closes the alternative: a guessable public file_url that would
# bypass the portal's customer-scope checks entirely.

PROTECTED_DOCTYPES = (
	"Forwarding Job",
	"Clearing Job",
	"Border Clearing Job",
	"Road Freight Job",
	"Warehouse Job",
	"Trip",
	"Sales Invoice",
	"Purchase Invoice",
)


def enforce_private_on_insert(doc, method=None):
	"""File before_insert hook: force is_private for job/invoice attachments."""
	if doc.attached_to_doctype in PROTECTED_DOCTYPES:
		doc.is_private = 1
