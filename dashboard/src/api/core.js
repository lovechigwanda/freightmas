// Shared fetch helper for all Command Center modules. Runs same-origin
// inside a logged-in Frappe Desk session, so the browser already carries the
// session cookie - we only need to attach the CSRF token Frappe exposes
// globally as window.csrf_token.
//
// Each module's api.js creates its own client bound to its whitelisted
// Python module path via createApiClient(prefix).

function buildUrl(prefix, method, params = {}) {
	const url = `/api/method/${prefix}.${method}`;
	const query = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value === undefined || value === null || value === "") return;
		query.append(key, typeof value === "object" ? JSON.stringify(value) : value);
	});
	return query.toString() ? `${url}?${query.toString()}` : url;
}

async function call(prefix, method, params = {}) {
	const fullUrl = buildUrl(prefix, method, params);

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

export function createApiClient(prefix) {
	return {
		call: (method, params) => call(prefix, method, params),
		buildUrl: (method, params) => buildUrl(prefix, method, params),
	};
}
