const STAGE_CHIP_LABELS = {
	"Sea / Air Freight": "Sea / Air",
	"Port Clearance": "Port",
	"Road Transport": "Road",
	"Border Clearance": "Border",
	Completion: "Completion",
};

const MILESTONE_KINDS = new Set(["sea_air", "clearance_checklist", "clearance_stages"]);

export function serviceTags(header, sections = []) {
	const parts = [];
	if (header?.direction) {
		parts.push(header.direction);
	}
	const titles = (sections || [])
		.filter((s) => s.kind !== "completion")
		.map((s) => STAGE_CHIP_LABELS[s.title] || s.title);
	if (titles.length) {
		parts.push(titles.join(", "));
	}
	return parts.join(" · ");
}

export function stageChips(sections = []) {
	return (sections || []).map((section) => ({
		key: section.title,
		label: STAGE_CHIP_LABELS[section.title] || section.title,
		done: section.progress?.done ?? 0,
		total: section.progress?.total ?? 0,
		percent: section.progress?.percent ?? 0,
		active: false,
	}));
}

export function markActiveStageChip(chips) {
	const next = chips.map((chip) => ({ ...chip }));
	const activeIdx = next.findIndex((chip) => chip.percent > 0 && chip.percent < 100);
	const idx = activeIdx >= 0 ? activeIdx : next.findIndex((chip) => chip.percent < 100);
	if (idx >= 0) {
		next[idx].active = true;
	}
	return next;
}

export function overallProgress(sections = [], fallbackPercent = 0) {
	let done = 0;
	let total = 0;
	for (const section of sections || []) {
		done += section.progress?.done ?? 0;
		total += section.progress?.total ?? 0;
	}
	if (total > 0) {
		return {
			done,
			total,
			percent: Math.round((done / total) * 100),
		};
	}
	return { done: 0, total: 0, percent: fallbackPercent || 0 };
}

export function milestoneSections(sections = []) {
	return (sections || []).filter((section) => MILESTONE_KINDS.has(section.kind));
}

export function completionSection(sections = []) {
	return (sections || []).find((section) => section.kind === "completion") || null;
}

export function seaAirSection(sections = []) {
	return (sections || []).find((section) => section.kind === "sea_air") || null;
}

export function roadSection(sections = []) {
	return (sections || []).find((section) => section.kind === "road") || null;
}

export function mergeCargoRows(seaSection, roadSection) {
	const byKey = new Map();

	for (const row of seaSection?.containers || []) {
		const key = row.container_number || row.name;
		byKey.set(key, {
			container_number: row.container_number,
			container_type: row.container_type,
			status: row.status,
			discharge_date: row.discharge_date,
			gate_out_date: row.gate_out_date,
			empty_return_date: row.empty_return_date,
			to_be_returned: row.to_be_returned,
			has_sea_air: true,
			has_road: false,
		});
	}

	for (const row of roadSection?.containers || []) {
		const key = row.container_number || row.name;
		const existing = byKey.get(key) || {
			container_number: row.container_number,
			container_type: row.container_type,
			has_sea_air: false,
			has_road: false,
		};
		byKey.set(key, {
			...existing,
			container_type: existing.container_type || row.container_type,
			cargo_type: row.cargo_type,
			to_be_returned: row.to_be_returned ?? existing.to_be_returned,
			is_booked: row.is_booked,
			is_loaded: row.is_loaded,
			is_offloaded: row.is_offloaded,
			is_returned: row.is_returned,
			is_completed: row.is_completed,
			booked_on_date: row.booked_on_date,
			loaded_on_date: row.loaded_on_date,
			offloaded_on_date: row.offloaded_on_date,
			returned_on_date: row.returned_on_date,
			completed_on_date: row.completed_on_date,
			empty_return_date: row.empty_return_date ?? existing.empty_return_date,
			status: existing.status || (row.is_completed ? "Delivered" : "In Transit"),
			has_sea_air: existing.has_sea_air,
			has_road: true,
		});
	}

	return [...byKey.values()];
}

export function progressTone(percent) {
	if (percent >= 100) return "done";
	if (percent > 0) return "partial";
	return "pending";
}
