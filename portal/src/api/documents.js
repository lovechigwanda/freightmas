import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.documents");

export const api = {
	getJobDocuments: (jobName) => client.call("get_job_documents", { job_name: jobName }),
	getUploadDocumentTypes: () => client.call("get_upload_document_types"),
	uploadDocument: (jobName, { file, checklistRow, document }) => {
		const formData = new FormData();
		formData.append("job_name", jobName);
		formData.append("file", file);
		if (checklistRow) formData.append("checklist_row", checklistRow);
		if (document) formData.append("document", document);
		return client.postFormData("upload_job_document", formData);
	},
	downloadDocumentUrl: (jobName, checklistRow) =>
		client.buildUrl("download_job_document", { job_name: jobName, checklist_row: checklistRow }),
};
