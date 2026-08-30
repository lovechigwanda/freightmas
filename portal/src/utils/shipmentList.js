import { Plane, Ship, Truck } from "@lucide/vue";
import { formatDate, formatDateShort } from "../format";

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
	on_road: "teal",
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

export function shipmentEquipmentLabel(job) {
	return job?.cargo_count || "–";
}

export function shipmentCargoChips(job) {
	const chips = [];
	if (job?.cargo_count) {
		chips.push({ label: job.cargo_count });
	} else if (job?.cargo_description) {
		chips.push({ label: job.cargo_description });
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

export function shipmentMilestoneLine(job) {
	const phase = shipmentPhaseLabel(job);
	let comment = job?.current_comment || "";
	if (!comment) {
		comment = phase === "–" ? "No tracking update yet" : "";
	}
	const shortDate = formatDateShort(job?.last_updated_on);
	return { phase, comment, shortDate };
}

export function shipmentEtaAtaDisplay(job) {
	const isExport = job?.direction === "Export";
	const actualDate = isExport ? job?.atd : job?.ata;
	const actualLabel = isExport ? "ATD" : "ATA";
	const estimatedDate = isExport ? job?.etd : job?.eta;
	const estimatedLabel = isExport ? "ETD" : "ETA";

	if (actualDate) {
		return {
			kind: "actual",
			label: actualLabel,
			date: actualDate,
			display: formatDate(actualDate),
			urgency: "normal",
		};
	}

	if (estimatedDate) {
		return {
			kind: "estimated",
			label: estimatedLabel,
			date: estimatedDate,
			display: formatDate(estimatedDate),
			urgency: job?.is_overdue ? "overdue" : "normal",
		};
	}

	return { kind: "none", display: "–", urgency: "normal" };
}

export function shipmentEtaLabel(job) {
	const etaAta = shipmentEtaAtaDisplay(job);
	if (etaAta.kind === "none") {
		const isExport = job?.direction === "Export";
		return { label: isExport ? "ETD" : "ETA", display: "–", urgency: "normal" };
	}

	return {
		label: etaAta.label,
		date: etaAta.date,
		display: `${etaAta.label} ${etaAta.display}`,
		urgency: etaAta.urgency,
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
