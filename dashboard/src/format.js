export function formatMoney(value, currency = "USD") {
	const n = Number(value || 0);
	try {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: currency || "USD",
			maximumFractionDigits: 0,
		}).format(n);
	} catch (e) {
		return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
	}
}

export function formatNumber(value) {
	return Number(value || 0).toLocaleString();
}

export function formatDate(value) {
	if (!value) return "\u2013";
	const d = new Date(value);
	if (Number.isNaN(d.getTime())) return value;
	return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value) {
	if (!value) return "\u2013";
	const d = new Date(value);
	if (Number.isNaN(d.getTime())) return value;
	return d.toLocaleString(undefined, {
		day: "2-digit",
		month: "short",
		year: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}

const STATUS_COLORS = {
	Draft: "#94a3b8",
	"In Progress": "#4f46e5",
	Delivered: "#16a34a",
	Completed: "#0d9488",
	Closed: "#64748b",
	Cancelled: "#dc2626",
};

const PALETTE = ["#4f46e5", "#0d9488", "#d97706", "#16a34a", "#dc2626", "#94a3b8", "#7c3aed", "#0891b2"];

export function statusColor(status, index = 0) {
	return STATUS_COLORS[status] || PALETTE[index % PALETTE.length];
}

export function initials(name) {
	if (!name) return "?";
	return name
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((w) => w[0].toUpperCase())
		.join("");
}
