import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "../modules/overview/api";
import { useFiltersStore } from "./filters";

// Caches the executive rollup so navigating away and back doesn't refetch, and
// centralises the refresh / auto-refresh behaviour used by the TopBar. The
// server already caches for ~5 min; this store avoids redundant client calls
// within a view session and gives a single place to trigger a hard refresh.
export const useOverviewStore = defineStore("overview", () => {
	const data = ref(null);
	const loading = ref(false);
	const error = ref("");
	const loadedAt = ref(null);
	let inflight = null;

	async function load({ force = false } = {}) {
		if (data.value && !force) return data.value;
		if (inflight) return inflight;

		const filters = useFiltersStore();
		loading.value = true;
		error.value = "";
		inflight = (async () => {
			try {
				data.value = await api.getExecutiveOverview({ company: filters.company || undefined });
				loadedAt.value = new Date();
			} catch (e) {
				error.value = (e && e.message) || "Failed to load executive overview.";
			} finally {
				loading.value = false;
				inflight = null;
			}
			return data.value;
		})();
		return inflight;
	}

	function refresh() {
		return load({ force: true });
	}

	return { data, loading, error, loadedAt, load, refresh };
});
