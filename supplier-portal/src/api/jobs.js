import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.supplier.jobs");

export const api = {
	getJobTypes: () => client.call("get_job_types"),
	getJobs: (params) => client.call("get_jobs", params),
	getJobDetail: (jobDoctype, jobName) =>
		client.call("get_job_detail", { job_doctype: jobDoctype, job_name: jobName }),
};
