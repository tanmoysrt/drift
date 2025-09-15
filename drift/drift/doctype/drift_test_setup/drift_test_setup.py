# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec

from drift.drift.utils import prepare_safe_exec_locals


class DriftTestSetup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default_local_variables: DF.JSON
		existing_user: DF.Link | None
		new_user_creation_script: DF.Code | None
		script_to_find_resources_to_cleanup: DF.Code
		user_type: DF.Literal["Existing User", "New User"]
	# end: auto-generated types

	def get_user(self, variables: frappe._dict | None) -> str:
		if self.user_type == "Existing User":
			if not self.existing_user:
				frappe.throw("Please select an existing user")
			if frappe.db.get_value("User", self.existing_user, "enabled") != 1:
				frappe.throw(f"User {self.existing_user} is disabled")
			return self.existing_user

		# Create new user
		if not self.new_user_creation_script:
			frappe.throw("Please provide a script to create a new user")

		local_vars = prepare_safe_exec_locals(variables or {})
		safe_exec(self.new_user_creation_script, _locals=local_vars)

		if "user" not in local_vars["variables"]:
			frappe.throw("The script must set the 'user' key in the 'variables' dictionary")
		user = local_vars["variables"].get("user")
		if not user:
			frappe.throw("The 'user' key in the 'variables' dictionary cannot be empty")
		if frappe.db.get_value("User", user, "enabled") != 1:
			frappe.throw(f"User {user} is disabled")
		return user
