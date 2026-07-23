import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.shipments");

export const api = {
	getJobs: (params) => client.call("get_jobs", params),
	getJobDetail: (jobName) => client.call("get_job_detail", { job_name: jobName }),
	exportTrackingReportUrl: (params) => client.buildUrl("export_tracking_report", params),
};
