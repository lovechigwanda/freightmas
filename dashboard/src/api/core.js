// Shared fetch helper for all Command Center modules. Runs same-origin
// inside a logged-in Frappe Desk session, so the browser already carries the
// session cookie - attach the CSRF token from frappe.csrf_token (Desk)
// or window.csrf_token (www portal pages).
//
// Each module's api.js creates its own client bound to its whitelisted
// Python module path via createApiClient(prefix).

const SESSION_EXPIRED_MESSAGE =
	"Your session has expired due to inactivity. Please log in again.";

function buildUrl(prefix, method, params = {}) {
	const url = `/api/method/${prefix}.${method}`;
	const query = new URLSearchParams();
	Object.entries(params).forEach(([key, value]) => {
		if (value === undefined || value === null || value === "") return;
		query.append(key, typeof value === "object" ? JSON.stringify(value) : value);
	});
	return query.toString() ? `${url}?${query.toString()}` : url;
}

// Frappe reports errors via a `_server_messages` field that is itself a
// JSON-encoded array of JSON-encoded {message, title, indicator} objects -
// double-encoded, not a plain string. Unwrap it so the UI can show a clean
// sentence instead of the raw nested-JSON payload.
function extractServerMessage(payload) {
	const raw = payload && payload._server_messages;
	if (!raw) return "";
	try {
		const messages = JSON.parse(raw);
		return messages
			.map((m) => {
				try {
					return JSON.parse(m).message;
				} catch (e) {
					return m;
				}
			})
			.filter(Boolean)
			.join(" ");
	} catch (e) {
		return "";
	}
}

function isSessionExpiry(status, message) {
	if (status !== 401 && status !== 403) return false;
	if (!message) return false;
	const lower = String(message).toLowerCase();
	return lower.includes("login to access") || lower.includes("not whitelisted");
}

function getCsrfToken() {
	return window.frappe?.csrf_token || window.csrf_token || "";
}

function handleSessionExpired() {
	if (typeof window.fmShowSessionExpiredDialog === "function") {
		window.fmShowSessionExpiredDialog();
	}
}

async function request(prefix, method, params = {}, { method: httpMethod = "GET" } = {}) {
	const url = httpMethod === "GET" ? buildUrl(prefix, method, params) : `/api/method/${prefix}.${method}`;

	const init = {
		method: httpMethod,
		credentials: "same-origin",
		headers: {
			"X-Frappe-CSRF-Token": getCsrfToken(),
			Accept: "application/json",
		},
	};

	if (httpMethod === "POST") {
		const body = new URLSearchParams();
		const csrfToken = getCsrfToken();
		if (csrfToken) {
			body.append("csrf_token", csrfToken);
		}
		Object.entries(params).forEach(([key, value]) => {
			if (value === undefined || value === null || value === "") return;
			body.append(key, typeof value === "object" ? JSON.stringify(value) : value);
		});
		init.body = body;
	}

	const res = await fetch(url, init);

	if (!res.ok) {
		let detail = "";
		try {
			detail = extractServerMessage(await res.json());
		} catch (e) {
			// ignore - not JSON
		}

		if (isSessionExpiry(res.status, detail)) {
			handleSessionExpired();
			throw new Error(SESSION_EXPIRED_MESSAGE);
		}

		throw new Error(detail || `Request to ${method} failed (${res.status}).`);
	}

	const data = await res.json();
	return data.message;
}

async function call(prefix, method, params = {}) {
	return request(prefix, method, params, { method: "GET" });
}

async function callPost(prefix, method, params = {}) {
	return request(prefix, method, params, { method: "POST" });
}

export function createApiClient(prefix) {
	return {
		call: (method, params) => call(prefix, method, params),
		callPost: (method, params) => callPost(prefix, method, params),
		buildUrl: (method, params) => buildUrl(prefix, method, params),
	};
}
