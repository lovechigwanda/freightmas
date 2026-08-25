import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.documents");

export const api = {
	getJobDocuments: (jobName) => client.call("get_job_documents", { job_name: jobName }),
	downloadDocumentUrl: (jobName, checklistRow) =>
		client.buildUrl("download_job_document", { job_name: jobName, checklist_row: checklistRow }),
};
