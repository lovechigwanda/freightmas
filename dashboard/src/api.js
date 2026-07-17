// Thin fetch wrapper around the whitelisted Shipment Dashboard API.
// Runs same-origin inside a logged-in Frappe Desk session, so the browser
// already carries the session cookie - we only need to attach the CSRF
// token Frappe exposes globally as window.csrf_token.

const METHOD_PREFIX = "freightmas.freightmas.page.shipment_dashboard.shipment_dashboard";

function buildUrl(method, params = {}) {
	const url = `/api/method/${METHOD_PREFIX}.${method}`;
	const query = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value === undefined || value === null || value === "") return;
		query.append(key, typeof value === "object" ? JSON.stringify(value) : value);
	});
	return query.toString() ? `${url}?${query.toString()}` : url;
}

async function call(method, params = {}) {
	const fullUrl = buildUrl(method, params);

	const res = await fetch(fullUrl, {
		method: "GET",
		credentials: "same-origin",
		headers: {
			"X-Frappe-CSRF-Token": window.csrf_token || "",
			Accept: "application/json",
		},
	});

	if (!res.ok) {
		let detail = "";
		try {
			detail = (await res.json())._server_messages || "";
		} catch (e) {
			// ignore - not JSON
		}
		throw new Error(`Request to ${method} failed (${res.status}). ${detail}`);
	}

	const data = await res.json();
	return data.message;
}

export const api = {
	getBranding: () => call("get_branding"),
	getOverview: () => call("get_overview"),
	getJobs: (params) => call("get_jobs", params),
	getJobDetail: (jobName) => call("get_job_detail", { job_name: jobName }),
	getFinanceSummary: (params) => call("get_finance_summary", params),
	getDndOverview: () => call("get_dnd_overview"),
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
	return buildUrl(methodMap[kind], params);
}
