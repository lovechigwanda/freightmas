import { Plane, Ship, Truck } from "@lucide/vue";
import { formatDate } from "../format";

const MODE_ICONS = {
	Sea: Ship,
	Air: Plane,
	Road: Truck,
};

const PHASE_TONE = {
	planning: "neutral",
	awaiting_departure: "neutral",
	in_transit: "blue",
	at_terminal: "teal",
	under_port_clearance: "purple",
	under_border_clearance: "orange",
	on_road: "amber",
	at_warehouse: "amber",
	delivered: "green",
	closed: "neutral",
	cancelled: "red",
};

export function shipmentPrimaryLabel(job) {
	return job?.customer_reference || job?.bl_number || job?.name || "–";
}

export function shipmentModeIcon(job) {
	return MODE_ICONS[job?.shipment_mode] || Ship;
}

export function shipmentCargoChips(job) {
	const chips = [];
	if (job?.cargo_count) {
		chips.push({ label: job.cargo_count });
	} else if (job?.cargo_description) {
		chips.push({ label: job.cargo_description });
	}
	if (job?.direction) {
		chips.push({ label: job.direction });
	}
	if (job?.shipment_type) {
		chips.push({ label: job.shipment_type });
	}
	return chips;
}

export function shipmentCargoLine(job) {
	const labels = shipmentCargoChips(job).map((chip) => chip.label);
	return labels.join(" · ") || "–";
}

export function shipmentPhaseLabel(job) {
	return job?.operational_phase_label || job?.operational_phase || "–";
}

export function shipmentPhaseTone(job) {
	return PHASE_TONE[job?.operational_phase] || "neutral";
}

export function shipmentHeadline(job) {
	if (job?.current_comment) {
		return job.current_comment;
	}
	if (job?.operational_phase_label) {
		return job.operational_phase_label;
	}
	const primary = shipmentPrimaryLabel(job);
	if (job?.name && job.name !== primary) {
		return job.name;
	}
	return "No tracking update yet";
}

export function shipmentEtaLabel(job) {
	const isExport = job?.direction === "Export";
	const date = isExport ? job?.etd : job?.eta;
	const label = isExport ? "ETD" : "ETA";

	if (!date) {
		return { label, display: "–", urgency: "normal" };
	}

	let urgency = "normal";
	if (job?.is_overdue) {
		urgency = "overdue";
	}

	return {
		label,
		date,
		display: `${label} ${formatDate(date)}`,
		urgency,
	};
}

export function shipmentMetaLine(job) {
	const parts = [job?.name].filter(Boolean);
	const eta = shipmentEtaLabel(job);
	if (eta.date) {
		parts.push(eta.display);
	}
	const isExport = job?.direction === "Export";
	const actualDate = isExport ? job?.atd : job?.ata;
	const actualLabel = isExport ? "ATD" : "ATA";
	if (actualDate) {
		parts.push(`${actualLabel} ${formatDate(actualDate)}`);
	} else if (eta.date) {
		parts.push(`${actualLabel} pending`);
	}
	return parts.join(" · ");
}

export function shipmentCompactSubline(job) {
	const parts = [shipmentHeadline(job)];
	const primary = shipmentPrimaryLabel(job);
	if (job?.name && job.name !== primary && job?.current_comment) {
		parts.push(job.name);
	}
	const eta = shipmentEtaLabel(job);
	if (eta.date && job?.current_comment) {
		parts.push(eta.display);
	}
	return parts.filter(Boolean).join(" · ");
}
