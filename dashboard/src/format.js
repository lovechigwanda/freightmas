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

const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function parseDateValue(value) {
	if (value instanceof Date) return value;
	if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
		const [year, month, day] = value.split("-").map(Number);
		return new Date(year, month - 1, day);
	}
	return new Date(value);
}

function formatDateParts(date) {
	const day = String(date.getDate()).padStart(2, "0");
	const month = SHORT_MONTHS[date.getMonth()];
	const year = String(date.getFullYear() % 100).padStart(2, "0");
	return `${day}-${month}-${year}`;
}

export function formatDate(value) {
	if (!value) return "\u2013";
	const d = parseDateValue(value);
	if (Number.isNaN(d.getTime())) return String(value);
	return formatDateParts(d);
}

/** Single date for list views: actual (ATA/ATD) when set, otherwise estimated (ETA/ETD). */
export function formatEstimatedOrActualDate(job) {
	if (!job) return "\u2013";
	const isExport = job.direction === "Export";
	const actual = isExport ? job.atd : job.ata;
	const estimated = isExport ? job.etd : job.eta;
	if (actual) return formatDate(actual);
	if (estimated) return formatDate(estimated);
	return "\u2013";
}

export function formatDateTime(value) {
	if (!value) return "\u2013";
	const d = parseDateValue(value);
	if (Number.isNaN(d.getTime())) return String(value);
	const timePart = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
	return `${formatDateParts(d)} ${timePart}`;
}

// Active chart palette, swapped by the theme store (stores/theme.js) whenever the
// user changes theme. `statusColor` is called synchronously from view computeds,
// so it reads this module-level mirror rather than the Pinia store directly.
// Defaults to the light theme's colours until the store applies one at startup.
let ACTIVE = {
	status: { Draft: "#94a3b8", "In Progress": "#4f46e5", Delivered: "#16a34a", Completed: "#0d9488", Closed: "#64748b", Cancelled: "#dc2626" },
	ramp: ["#4f46e5", "#0d9488", "#d97706", "#16a34a", "#dc2626", "#94a3b8", "#7c3aed", "#0891b2"],
};

export function setActivePalette(palette) {
	if (palette && palette.status && palette.ramp) ACTIVE = palette;
}

export function statusColor(status, index = 0) {
	return ACTIVE.status[status] || ACTIVE.ramp[index % ACTIVE.ramp.length];
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
