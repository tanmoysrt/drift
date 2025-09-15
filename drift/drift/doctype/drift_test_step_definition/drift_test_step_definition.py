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

	pass
