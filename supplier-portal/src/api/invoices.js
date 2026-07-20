import { createApiClient } from "./core";

const client = createApiClient("freightmas.portal.supplier.invoices");

export const api = {
	getInvoices: (params) => client.call("get_invoices", params),
	getInvoiceDetail: (invoiceName) => client.call("get_invoice_detail", { invoice_name: invoiceName }),
};
