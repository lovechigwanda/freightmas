// Thin API client for the Forwarding module, bound to the whitelisted
// shipment_dashboard Python module (kept at its original path/name - it
// predates the multi-module Command Center and works fine as-is).
import { createApiClient } from "../../api/core";

const client = createApiClient("freightmas.freightmas.page.shipment_dashboard.shipment_dashboard");

export const api = {
	getOverview: () => client.call("get_overview"),
	getJobs: (params) => client.call("get_jobs", params),
	getJobDetail: (jobName) => client.call("get_job_detail", { job_name: jobName }),
	getFinanceSummary: (params) => client.call("get_finance_summary", params),
	getDndOverview: () => client.call("get_dnd_overview"),
};

// Export endpoints stream a binary xlsx response directly - navigating to the
// URL (new tab / window.location) triggers the browser's normal file download,
// no fetch/blob juggling needed. GET requests to whitelisted methods don't
// require the CSRF header, so a plain URL is enough.
export function exportUrl(kind, params = {}) {
	const methodMap = {
		shipments: "export_jobs",
		finance: "export_finance",
		dnd: "export_dnd",
	};
	return client.buildUrl(methodMap[kind], params);
}

