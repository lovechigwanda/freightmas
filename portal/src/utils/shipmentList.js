import { formatDate } from "../format";

export function shipmentPrimaryLabel(job) {
	return job?.customer_reference || job?.bl_number || job?.name || "–";
}

export function shipmentCargoLine(job) {
	const parts = [];
	if (job?.cargo_count) {
		parts.push(job.cargo_count);
	}
	if (job?.cargo_description) {
		parts.push(job.cargo_description);
	}
	if (job?.direction) {
		parts.push(job.direction);
	}
	if (job?.shipment_type) {
		parts.push(job.shipment_type);
	}
	return parts.join(" · ") || "–";
}

export function shipmentMetaLine(job) {
	const parts = [job?.name].filter(Boolean);
	const isExport = job?.direction === "Export";
	const primaryDate = isExport ? job?.etd : job?.eta;
	const actualDate = isExport ? job?.atd : job?.ata;
	const dateLabel = isExport ? "ETD" : "ETA";
	const actualLabel = isExport ? "ATD" : "ATA";

	if (primaryDate) {
		parts.push(`${dateLabel} ${formatDate(primaryDate)}`);
	}
	if (actualDate) {
		parts.push(`${actualLabel} ${formatDate(actualDate)}`);
	} else if (primaryDate) {
		parts.push(`${actualLabel} pending`);
	}
	return parts.join(" · ");
}
