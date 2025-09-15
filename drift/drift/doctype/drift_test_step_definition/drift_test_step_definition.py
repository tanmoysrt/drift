# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DriftTestStepDefinition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		server_script: DF.Code | None
		timeout_seconds: DF.Int
		title: DF.Data
		type: DF.Literal["UI Navigation", "Server Script", "Setup User Session"]
		ui_navigation_goto_url: DF.Data | None
		ui_navigation_type: DF.Literal["Goto", "Reload", "Forward", "Backward"]
		wait_for_completion: DF.Check
	# end: auto-generated types

	@property
	def code(self) -> str:
		if self.type == "Server Script":
			return self.server_script or ""
		elif self.type == "UI Navigation":
			if self.ui_navigation_type == "Goto" and self.ui_navigation_goto_url:
				return f"""pw_page.goto("{self.ui_navigation_goto_url}",wait_until="domcontentloaded")"""
			elif self.ui_navigation_type == "Reload":
				return """pw_page.reload(wait_until="domcontentloaded")"""
			elif self.ui_navigation_type == "Forward":
				return """pw_page.go_forward(wait_until="domcontentloaded")"""
			elif self.ui_navigation_type == "Backward":
				return """pw_page.go_back(wait_until="domcontentloaded")"""
		elif self.type == "Setup User Session":
			return """
setup = frappe.get_doc("Drift Test Setup", frappe.db.get_value("Drift Test Definition", doc.definition, "test_setup"))
user = setup.get_user(variables)

variables["session_user"] = user
variables["session_user_sid"] = get_login_sid(user)
"""

		return ""
