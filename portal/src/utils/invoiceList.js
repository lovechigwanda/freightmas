import { FileText, Receipt } from "@lucide/vue";
import { formatDate, formatMoney } from "../format";

export function invoicePrimaryLabel(invoice) {
	if (invoice.job_customer_reference) {
		return invoice.job_customer_reference;
	}
	return invoice.name;
}

export function invoiceListIcon(invoice) {
	return invoiceIsCredit(invoice) ? FileText : Receipt;
}

export function invoiceContextChips(invoice) {
	const chips = [];
	if (invoice.job_name) {
		chips.push({ label: invoice.job_name });
	}
	if (invoice.job_cargo_count) {
		chips.push({ label: `${invoice.job_cargo_count} container(s)` });
	} else if (invoice.job_cargo_description) {
		chips.push({ label: invoice.job_cargo_description });
	}
	return chips;
}

export function invoiceContextLine(invoice) {
	const labels = invoiceContextChips(invoice).map((chip) => chip.label);
	return labels.length ? labels.join(" · ") : "No linked shipment";
}

export function invoiceDueLabel(invoice) {
	if (!invoice.due_date) {
		return { display: "–", urgency: "normal" };
	}
	return {
		display: `Due ${formatDate(invoice.due_date)}`,
		urgency: invoice.is_overdue ? "overdue" : "normal",
	};
}

export function invoiceSecondaryMeta(invoice) {
	return invoice.name || "–";
}

export function invoiceMetaLine(invoice) {
	const parts = [invoiceSecondaryMeta(invoice)];
	if (invoice.posting_date) {
		parts.push(`Posted ${formatDate(invoice.posting_date)}`);
	}
	const due = invoiceDueLabel(invoice);
	if (invoice.due_date) {
		parts.push(due.display);
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
