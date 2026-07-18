import { defineStore } from "pinia";
import { ref, watch } from "vue";

// Shared, cross-module filter model. The executive overview and each module view
// read/write the same company / date-range / customer here, so drilling from the
// landing page into a module preserves the analyst's context. Persisted to
// sessionStorage so a Desk page reload keeps the selection.

const STORAGE_KEY = "fm_cc_filters";

function loadPersisted() {
	if (typeof window === "undefined") return {};
	try {
		return JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || "{}") || {};
	} catch (e) {
		return {};
	}
}

// Default window: last 90 days, ISO yyyy-mm-dd (Frappe's date format).
function isoDaysAgo(days) {
	const d = new Date();
	d.setDate(d.getDate() - days);
	return d.toISOString().slice(0, 10);
}

export const useFiltersStore = defineStore("filters", () => {
	const saved = loadPersisted();

	const company = ref(saved.company || null);
	const customer = ref(saved.customer || null);
	const fromDate = ref(saved.fromDate || isoDaysAgo(90));
	const toDate = ref(saved.toDate || new Date().toISOString().slice(0, 10));

	function setDateRange(from, to) {
		fromDate.value = from;
		toDate.value = to;
	}

	function reset() {
		company.value = null;
		customer.value = null;
		fromDate.value = isoDaysAgo(90);
		toDate.value = new Date().toISOString().slice(0, 10);
	}

	// Persist any change so it survives a page reload within the session.
	watch([company, customer, fromDate, toDate], () => {
		if (typeof window === "undefined") return;
		window.sessionStorage.setItem(
			STORAGE_KEY,
			JSON.stringify({
				company: company.value,
				customer: customer.value,
				fromDate: fromDate.value,
				toDate: toDate.value,
			})
		);
	});

	return { company, customer, fromDate, toDate, setDateRange, reset };
});
