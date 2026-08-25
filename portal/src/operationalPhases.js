import {
	MapPin,
	Waves,
	Anchor,
	FileCheck,
	ShieldCheck,
	Truck,
	PackageCheck,
} from "@lucide/vue";

export const OPERATIONAL_PHASES = [
	{ value: "", label: "All Phases" },
	{ value: "planning", label: "Planning" },
	{ value: "awaiting_departure", label: "Awaiting Departure" },
	{ value: "in_transit", label: "In Transit" },
	{ value: "at_terminal", label: "At Terminal" },
	{ value: "under_port_clearance", label: "Under Port Clearance" },
	{ value: "under_border_clearance", label: "Under Border Clearance" },
	{ value: "on_road", label: "On Road" },
	{ value: "at_warehouse", label: "At Warehouse" },
	{ value: "delivered", label: "Delivered" },
	{ value: "closed", label: "Closed" },
	{ value: "cancelled", label: "Cancelled" },
];

/** Checkbox options for the Shipments phase multi-select (excludes "All Phases"). */
export const OPERATIONAL_PHASE_OPTIONS = OPERATIONAL_PHASES.filter((phase) => phase.value);

/** Icons and accent tones for overview pipeline cards (keys match backend buckets). */
export const OVERVIEW_PIPELINE_META = {
	at_origin: { icon: MapPin, tone: "neutral" },
	in_transit: { icon: Waves, tone: "blue" },
	at_terminal: { icon: Anchor, tone: "teal" },
	under_port_clearance: { icon: FileCheck, tone: "purple" },
	under_border_clearance: { icon: ShieldCheck, tone: "orange" },
	on_road: { icon: Truck, tone: "amber" },
	delivered: { icon: PackageCheck, tone: "green" },
};

/** Phase values per overview pipeline bucket (mirrors backend OVERVIEW_PIPELINE_BUCKETS). */
export const OVERVIEW_BUCKET_PHASES = {
	at_origin: ["planning", "awaiting_departure"],
	in_transit: ["in_transit"],
	at_terminal: ["at_terminal"],
	under_port_clearance: ["under_port_clearance"],
	under_border_clearance: ["under_border_clearance"],
	on_road: ["on_road"],
	delivered: ["delivered"],
};

export function formatOperationalPhase(job) {
	if (!job?.operational_phase) return "–";
	const label = job.operational_phase_label || job.operational_phase;
	if (job.operational_substage) {
		return `${label} · ${job.operational_substage}`;
	}
	return label;
}

export function phasesFromBucket(bucket) {
	return OVERVIEW_BUCKET_PHASES[bucket] ? [...OVERVIEW_BUCKET_PHASES[bucket]] : [];
}

export function parsePhasesQuery(value) {
	if (!value) return [];
	if (Array.isArray(value)) {
		return value.flatMap((entry) => parsePhasesQuery(entry));
	}
	if (typeof value !== "string") return [];
	return value.split(",").map((phase) => phase.trim()).filter(Boolean);
}

export function phasesToQuery(phases) {
	return phases.filter(Boolean).join(",");
}
