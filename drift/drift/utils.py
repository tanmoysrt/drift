import frappe
from frappe.auth import CookieManager, LoginManager
from frappe.utils import set_request


def prepare_safe_exec_locals(variables: dict) -> dict:
	import re
	import time
	from time import sleep

	from playwright import sync_api

	locals_data = {"variables": frappe._dict(variables or {})}

	locals_data["pw"] = frappe._dict(
		{attr: getattr(sync_api, attr) for attr in sync_api.__all__ if not attr.startswith("_")}
	)
	locals_data["re"] = re
	locals_data["get_login_sid"] = get_login_sid
	locals_data["time"] = time
	locals_data["sleep"] = sleep
	return locals_data


def get_login_sid(user: str) -> str | None:
	current_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		set_request(path="/")
		frappe.local.cookie_manager = CookieManager()
		frappe.local.login_manager = LoginManager()
		frappe.local.request_ip = "127.0.0.1"
		frappe.local.login_manager.login_as(str(user))
		return frappe.session.sid
	except Exception:
		return None
	finally:
		frappe.set_user(current_user)
