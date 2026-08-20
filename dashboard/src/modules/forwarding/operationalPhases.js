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

export function formatOperationalPhase(job) {
	if (!job?.operational_phase) return "–";
	const label = job.operational_phase_label || job.operational_phase;
	if (job.operational_substage) {
		return `${label} · ${job.operational_substage}`;
	}
	return label;
}
