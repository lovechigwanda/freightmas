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
	getCustomers: () => client.call("get_customers"),
	getCustomerTrackingInfo: (customer) => client.call("get_customer_tracking_info", { customer }),
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
		trackingReport: "export_tracking_report",
		masterTrackingReport: "export_master_tracking_report",
		shipmentTrackingReport: "export_shipment_tracking_report",
		shipmentTrackingReportExcel: "export_shipment_tracking_report_excel",
	};
	return client.buildUrl(methodMap[kind], params);
}

// Mirrors exportUrl's methodMap - one whitelisted "email_*" function per
// report row. Uses POST (not GET) so message bodies and customer filters
// are not limited by URL length. Backend sends immediately (delayed=False)
// via Resend API when Resend Settings is enabled.
const emailMethodMap = {
	trackingReport: "email_tracking_report",
	masterTrackingReport: "email_master_tracking_report",
	shipmentTrackingReport: "email_shipment_tracking_report",
	shipmentTrackingReportExcel: "email_shipment_tracking_report_excel",
};
export function sendReportEmail(kind, params = {}) {
	return client.callPost(emailMethodMap[kind], params);
}

