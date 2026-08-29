import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.quotations");

export const api = {
	getQuotations: (params) => client.call("get_quotations", params),
	getQuotationsSummary: () => client.call("get_quotations_summary"),
	getQuotationDetail: (quotationName) =>
		client.call("get_quotation_detail", { quotation_name: quotationName }),
	getJobQuotations: (jobName) => client.call("get_job_quotations", { job_name: jobName }),
	downloadPdfUrl: (quotationName) =>
		client.buildUrl("download_quotation_pdf", { quotation_name: quotationName }),
	approveQuotation: (quotationName) =>
		client.post("approve_quotation", { quotation_name: quotationName }),
	rejectQuotation: (quotationName, reason) =>
		client.post("reject_quotation", { quotation_name: quotationName, reason }),
};
