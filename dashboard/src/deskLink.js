// Deterministic Frappe Desk URLs so any document reference in the read-only
// Command Center can be opened for editing in Desk (new tab). The dashboard
// itself stays read-only; Desk is where writes happen.
//
// Desk form URL = /app/<doctype-slug>/<name>, where the slug is the doctype
// lowercased with spaces -> hyphens. The explicit map documents the doctypes we
// link to and guarantees the right slug even if Frappe's convention ever drifts;
// the fallback derives it generically for anything not listed.

const SLUG = {
	"Forwarding Job": "forwarding-job",
	"Clearing Job": "clearing-job",
	"Border Clearing Job": "border-clearing-job",
	"Road Freight Job": "road-freight-job",
	"Trip": "trip",
	"Warehouse Job": "warehouse-job",
	"Master Forwarding Job": "master-forwarding-job",
	"Sales Invoice": "sales-invoice",
	"Purchase Invoice": "purchase-invoice",
	"Invoice Register Entry": "invoice-register-entry",
	"Invoicing Instruction": "invoicing-instruction",
	"Customer Goods Receipt": "customer-goods-receipt",
	"Customer Goods Dispatch": "customer-goods-dispatch",
	"Cash Reconciliation": "cash-reconciliation",
	Customer: "customer",
	Supplier: "supplier",
};

export function deskSlug(doctype) {
	return SLUG[doctype] || String(doctype || "").toLowerCase().replace(/\s+/g, "-");
}

export function deskUrl(doctype, name) {
	if (!doctype || !name) return "#";
	return `/app/${deskSlug(doctype)}/${encodeURIComponent(name)}`;
}

// List view for a doctype (e.g. the TopBar "Open in Desk" affordance).
export function deskListUrl(doctype) {
	if (!doctype) return "/app";
	return `/app/${deskSlug(doctype)}`;
}
