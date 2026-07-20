import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "../api/profile";

// User/supplier context, fetched exactly once per app load. Unlike the
// Command Center (a Desk Page, where window.frappe.session is already
// populated by desk.html), this is a plain www/ page - portal users never
// load Desk's boot JS, so the frontend fetches its own context instead.
export const useSessionStore = defineStore("session", () => {
	const fullName = ref("");
	const suppliers = ref([]);
	const loaded = ref(false);
	const error = ref("");
	let inflight = null;

	async function load() {
		if (loaded.value) return;
		if (inflight) return inflight;
		inflight = (async () => {
			try {
				const data = await api.getProfile();
				fullName.value = (data && data.full_name) || "";
				suppliers.value = (data && data.suppliers) || [];
			} catch (e) {
				error.value = e.message || "Failed to load your account.";
			} finally {
				loaded.value = true;
				inflight = null;
			}
		})();
		return inflight;
	}

	return { fullName, suppliers, loaded, error, load };
});
