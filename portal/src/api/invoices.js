import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.api.invoices");

export const api = {
	getInvoices: (params) => client.call("get_invoices", params),
	getInvoicesSummary: () => client.call("get_invoices_summary"),
	getInvoiceDetail: (invoiceName) => client.call("get_invoice_detail", { invoice_name: invoiceName }),
	downloadPdfUrl: (invoiceName) => client.buildUrl("download_invoice_pdf", { invoice_name: invoiceName }),
};
