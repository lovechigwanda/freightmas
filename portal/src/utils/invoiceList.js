import { formatDate, formatMoney } from "../format";

export function invoicePrimaryLabel(invoice) {
	if (invoice.job_customer_reference) {
		return invoice.job_customer_reference;
	}
	return invoice.name;
}

export function invoiceContextLine(invoice) {
	const parts = [];
	if (invoice.job_name) {
		parts.push(invoice.job_name);
	}
	if (invoice.job_cargo_count) {
		parts.push(`${invoice.job_cargo_count} container(s)`);
	} else if (invoice.job_cargo_description) {
		parts.push(invoice.job_cargo_description);
	}
	return parts.length ? parts.join(" · ") : "No linked shipment";
}

export function invoiceMetaLine(invoice) {
	const parts = [invoice.name];
	if (invoice.posting_date) {
		parts.push(`Posted ${formatDate(invoice.posting_date)}`);
	}
	if (invoice.due_date) {
		parts.push(`Due ${formatDate(invoice.due_date)}`);
	}
	return parts.join(" · ");
}

export function invoiceBalanceLabel(invoice) {
	if (invoice.is_return) {
		return "Credit";
	}
	if ((invoice.outstanding_amount || 0) > 0) {
		return "Balance due";
	}
	return "Amount";
}

export function invoiceBalanceAmount(invoice) {
	const outstanding = invoice.outstanding_amount || 0;
	if (outstanding > 0) {
		return formatMoney(outstanding);
	}
	return formatMoney(invoice.grand_total);
}

export function invoiceIsCredit(invoice) {
	return Boolean(invoice.is_return) || (invoice.grand_total || 0) < 0;
}

export const AGING_BUCKETS = [
	{ key: "current", label: "Current" },
	{ key: "1_30", label: "1–30 days" },
	{ key: "31_60", label: "31–60 days" },
	{ key: "61_90", label: "61–90 days" },
	{ key: "over_90", label: "90+ days" },
];
