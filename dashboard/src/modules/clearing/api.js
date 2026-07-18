// API client for the Clearing module, bound to the whitelisted
// clearing_dashboard Python controller.
import { createApiClient } from "../../api/core";

const client = createApiClient("freightmas.clearing_service.page.clearing_dashboard.clearing_dashboard");

export const api = {
	getOverview: () => client.call("get_overview"),
	getJobs: (params) => client.call("get_jobs", params),
	getJobDetail: (jobName) => client.call("get_job_detail", { job_name: jobName }),
	getFinanceSummary: (params) => client.call("get_finance_summary", params),
};

export function exportUrl(kind, params = {}) {
	const methodMap = { jobs: "export_jobs", finance: "export_finance" };
	return client.buildUrl(methodMap[kind], params);
}
