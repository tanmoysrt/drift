# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DriftTestStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		duration: DF.Duration | None
		error: DF.Data | None
		last_attempted_at: DF.Datetime | None
		no_of_attempts: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		started_at: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		step: DF.Link
		traceback: DF.Code | None
		wait_for_completion: DF.Check
	# end: auto-generated types

	pass
