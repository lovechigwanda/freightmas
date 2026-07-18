import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "../modules/overview/api";

// Branding + current-user context, fetched exactly once per app load and shared
// by the shell (Sidebar/TopBar) and every module. Replaces the previous pattern
// where App.vue and the Overview page each fetched branding independently.
export const useSessionStore = defineStore("session", () => {
	const branding = ref({ company_name: "FreightMas" });
	const loaded = ref(false);
	let inflight = null;

	// Frappe injects the logged-in user's context on window.frappe.
	const frappeSession = (typeof window !== "undefined" && window.frappe && window.frappe.session) || {};
	const user = ref(frappeSession.user || null);
	const userFullname = ref(frappeSession.user_fullname || frappeSession.user || null);
	const roles = ref((typeof window !== "undefined" && window.frappe && window.frappe.user_roles) || []);

	async function loadBranding() {
		if (loaded.value) return branding.value;
		if (inflight) return inflight; // dedupe concurrent callers
		inflight = (async () => {
			try {
				const data = await api.getBranding();
				if (data) branding.value = data;
			} catch (e) {
				branding.value = { company_name: "FreightMas" };
			} finally {
				loaded.value = true;
				inflight = null;
			}
			return branding.value;
		})();
		return inflight;
	}

	return { branding, loaded, user, userFullname, roles, loadBranding };
});
