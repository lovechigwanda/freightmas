/* FreightMas Session Expiry Handler
 * Intercepts session-expired AJAX errors and shows a user-friendly
 * "Session Expired" dialog instead of the default "Method Not Allowed" error.
 *
 * Background requests (e.g. notification bell polling get_notification_logs)
 * keep firing after the server session ends. Frappe's default 403 handler
 * shows a technical "Method Not Allowed" msgprint because the client still
 * thinks the user is logged in. This script suppresses those messages and
 * shows a single friendly dialog instead.
 */

(function () {
	let sessionExpiredDialogShown = false;

	function isSessionExpiryContent(text) {
		if (!text) return false;
		const lower = String(text).toLowerCase();
		return lower.includes("login to access") || lower.includes("not whitelisted");
	}

	function isSessionExpiryMessage(msg, title) {
		if (Array.isArray(msg)) {
			return msg.some((entry) => isSessionExpiryMessage(entry));
		}

		let message = "";
		let msgTitle = title || "";

		if ($.isPlainObject(msg)) {
			message = msg.message || "";
			msgTitle = msg.title || msgTitle;
		} else if (typeof msg === "string") {
			if (msg.charAt(0) === "{") {
				try {
					const parsed = JSON.parse(msg);
					message = parsed.message || "";
					msgTitle = parsed.title || msgTitle;
				} catch (e) {
					message = msg;
				}
			} else {
				message = msg;
			}
		}

		return isSessionExpiryContent(msgTitle + " " + message);
	}

	function hideExistingErrorDialogs() {
		if (frappe.msg_dialog && frappe.msg_dialog.$wrapper) {
			frappe.msg_dialog.hide();
		}
		if (frappe.error_dialog && frappe.error_dialog.$wrapper) {
			frappe.error_dialog.hide();
		}
	}

	function showSessionExpiredDialog() {
		if (sessionExpiredDialogShown) return;
		sessionExpiredDialogShown = true;

		// Align client session state with the server so later 403s route here
		// instead of opening more permission error dialogs.
		if (frappe.app && frappe.app.set_as_guest) {
			frappe.app.set_as_guest();
		}
		if (frappe.app) {
			frappe.app.handle_session_expired = showSessionExpiredDialog;
		}

		hideExistingErrorDialogs();

		const d = new frappe.ui.Dialog({
			title: __("Session Expired"),
			primary_action_label: __("Log In"),
			primary_action: function () {
				window.location.href = "/login";
			},
		});

		d.$body.html(
			'<div style="text-align:center; padding: 15px 0;">' +
				'<div style="font-size: 48px; margin-bottom: 15px;">&#x1F512;</div>' +
				"<p>" +
				__("Your session has expired due to inactivity.") +
				"<br>" +
				__("Please log in again to continue.") +
				"</p>" +
				"</div>"
		);

		d.on_hide = function () {
			window.location.href = "/login";
		};

		d.show();
	}

	function installMsgprintHook() {
		if (!frappe.msgprint || frappe.msgprint.__fmSessionHook) return;

		const originalMsgprint = frappe.msgprint;
		frappe.msgprint = function (msg, title, is_minimizable, re_route) {
			if (isSessionExpiryMessage(msg, title)) {
				showSessionExpiredDialog();
				return;
			}
			return originalMsgprint.call(this, msg, title, is_minimizable, re_route);
		};
		frappe.msgprint.__fmSessionHook = true;
	}

	installMsgprintHook();
	$(document).ready(installMsgprintHook);

	$(document).ajaxError(function (event, xhr) {
		if (xhr.status !== 403 && xhr.status !== 401) return;

		let responseText = "";
		try {
			responseText = xhr.responseText || "";
		} catch (e) {
			return;
		}

		if (isSessionExpiryContent(responseText)) {
			showSessionExpiredDialog();
		}
	});
})();
