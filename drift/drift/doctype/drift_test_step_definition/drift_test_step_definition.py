# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import get_url


class DriftTestStepDefinition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		playwright_action: DF.Literal["Click", "Double Click", "Mark Checkbox", "Unmark Checkbox", "Fill Text", "Select Option", "Clear Field"]
		playwright_action_timeout_sec: DF.Int
		playwright_action_value: DF.Data | None
		playwright_custom_locator: DF.Data | None
		playwright_locator_exact_match: DF.Check
		playwright_locator_role: DF.Literal["button", "link", "textbox", "checkbox", "radio", "switch", "combobox", "listbox", "option", "list", "listitem", "tab", "tablist", "tabpanel", "menu", "menubar", "menuitem", "dialog", "alert", "alertdialog", "tooltip", "progressbar", "slider", "navigation", "form", "main", "banner", "contentinfo", "region", "search", "heading", "article", "table", "row", "cell", "columnheader"]
		playwright_locator_text: DF.Data | None
		playwright_locator_type: DF.Literal["Get By Label", "Get By Role", "Get By Text", "Get By Placeholder", "Custom Locator"]
		playwright_wait_for_load_state: DF.Literal["Load", "DOM Content Loaded", "Network Idle"]
		playwright_wait_for_url_pattern: DF.Data | None
		playwright_wait_timeout_sec: DF.Int
		playwright_wait_type: DF.Literal["Load State", "URL Pattern"]
		server_script: DF.Code | None
		timeout_seconds: DF.Int
		title: DF.Data
		type: DF.Literal["Playwright Action", "UI Navigation", "Playwright Wait", "Wait", "Setup User Session", "Server Script"]
		ui_navigation_goto_url: DF.Data | None
		ui_navigation_type: DF.Literal["Goto", "Reload", "Forward", "Backward"]
		wait_duration_sec: DF.Int
		wait_for_completion: DF.Check
	# end: auto-generated types

	def db_insert(self, ignore_if_duplicate=False):
		self.auto_set_fields()
		return super().db_insert(ignore_if_duplicate)

	def db_update(self):
		self.auto_set_fields()
		return super().db_update()

	def auto_set_fields(self):
		if self.type == "Playwright Action":
			if not self.playwright_action_timeout_sec:
				self.playwright_action_timeout_sec = 30
			self.wait_for_completion = True
			self.timeout_seconds = max(self.timeout_seconds, self.playwright_action_timeout_sec)

		if self.type == "Playwright Wait" and not self.playwright_wait_timeout_sec:
			if not self.playwright_wait_timeout_sec:
				self.playwright_wait_timeout_sec = 30
			self.wait_for_completion = True
			self.timeout_seconds = max(self.timeout_seconds, self.playwright_wait_timeout_sec)

	def get_code(self, local_context: dict) -> str:
		if self.type == "Server Script":
			return self.server_script or ""

		if self.type == "Wait":
			return f"""
sleep({self.wait_duration_sec})
"""

		if self.type == "Setup User Session":
			return """
setup = frappe.get_doc("Drift Test Setup", frappe.db.get_value("Drift Test Definition", doc.definition, "test_setup"))
user = setup.get_user(variables)

variables["session_user"] = user
variables["session_user_sid"] = get_login_sid(user)
"""

		if self.type == "UI Navigation":
			if self.ui_navigation_type == "Goto" and self.ui_navigation_goto_url:
				url = get_url(self.render_jinja(self.ui_navigation_goto_url, local_context))
				return f"""pw_page.goto("{url}",wait_until="domcontentloaded")"""
			elif self.ui_navigation_type == "Reload":
				return """pw_page.reload(wait_until="domcontentloaded")"""
			elif self.ui_navigation_type == "Forward":
				return """pw_page.go_forward(wait_until="domcontentloaded")"""
			elif self.ui_navigation_type == "Backward":
				return """pw_page.go_back(wait_until="domcontentloaded")"""

		if self.type == "Playwright Wait":
			if self.playwright_wait_type == "Load State":
				load_state = {
					"Load": "load",
					"DOM Content Loaded": "domcontentloaded",
					"Network Idle": "networkidle",
				}[self.playwright_wait_for_load_state]
				return f"""
try:
	pw_page.wait_for_load_state("{load_state}", timeout={min(5000, self.playwright_wait_timeout_sec * 1000)})
	result = (True, False)
except pw.TimeoutError:
	result = (False, False)
except Exception as e:
	raise e
"""
			if self.playwright_wait_type == "URL Pattern":
				url = get_url(self.render_jinja(self.playwright_wait_for_url_pattern or "", local_context))

				return f"""
try:
	pw_page.wait_for_url("{url}", timeout={min(5000, self.playwright_wait_timeout_sec * 1000)})
	result = (True, False)
except pw.TimeoutError:
	result = (False, False)
except Exception as e:
	raise e
"""

		if self.type == "Playwright Action":
			# Prepare locator code
			locator_code = ""
			locator_text = self.render_jinja(self.playwright_locator_text or "", local_context)
			if self.playwright_locator_type == "Get By Label":
				locator_code = f'pw_page.get_by_label("{locator_text}", exact={self.bool_to_str(self.playwright_locator_exact_match)})'
			elif self.playwright_locator_type == "Get By Text":
				locator_code = f'pw_page.get_by_text("{locator_text}", exact={self.bool_to_str(self.playwright_locator_exact_match)})'
			elif self.playwright_locator_type == "Get By Role":
				locator_code = f'pw_page.get_by_role("{self.playwright_locator_role}", name="{locator_text}", exact={self.bool_to_str(self.playwright_locator_exact_match)})'
			elif self.playwright_locator_type == "Get By Placeholder":
				locator_code = f'pw_page.get_by_placeholder("{locator_text}", exact={self.bool_to_str(self.playwright_locator_exact_match)})'
			elif self.playwright_locator_type == "Custom Locator":
				locator_code = (
					f'pw_page.locator("{self.render_jinja(self.playwright_custom_locator, local_context)}")'
				)

			if not locator_code:
				return ""

			# Prepare action code
			action_code = ""
			if self.playwright_action == "Click":
				action_code = f"click(timeout={self.playwright_action_timeout_sec * 1000})"
			elif self.playwright_action == "Double Click":
				action_code = f"dblclick(timeout={self.playwright_action_timeout_sec * 1000})"
			elif self.playwright_action == "Mark Checkbox":
				action_code = f"check(timeout={self.playwright_action_timeout_sec * 1000})"
			elif self.playwright_action == "Unmark Checkbox":
				action_code = f"uncheck(timeout={self.playwright_action_timeout_sec * 1000})"
			elif self.playwright_action == "Fill Text":
				value = self.render_jinja(self.playwright_action_value or "", local_context)
				action_code = f'fill("{value}", timeout={self.playwright_action_timeout_sec * 1000})'
			elif self.playwright_action == "Select Option":
				value = self.render_jinja(self.playwright_action_value or "", local_context)
				action_code = f'select_option("{value}", timeout={self.playwright_action_timeout_sec * 1000})'
			elif self.playwright_action == "Clear Field":
				action_code = f"clear(timeout={self.playwright_action_timeout_sec * 1000})"

			if not action_code:
				return ""

			return f"{locator_code}.{action_code}"

		return ""

	def render_jinja(self, template: str, context: dict) -> str:
		from frappe.utils.jinja import render_template

		return render_template(template, context)

	def bool_to_str(self, value: bool) -> str:
		return "True" if value else "False"
