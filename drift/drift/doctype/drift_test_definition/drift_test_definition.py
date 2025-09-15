# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from drift.drift.doctype.drift_settings.drift_settings import get_random_session_server

if TYPE_CHECKING:
	from drift.drift.doctype.drift_test.drift_test import DriftTest


class DriftTestDefinition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from drift.drift.doctype.drift_test_step_definition.drift_test_step_definition import (
			DriftTestStepDefinition,
		)

		enabled: DF.Check
		interval_minutes: DF.Int
		last_executed_on: DF.Datetime | None
		next_execution_on: DF.Datetime | None
		steps: DF.Table[DriftTestStepDefinition]
		test_setup: DF.Link
	# end: auto-generated types

	@frappe.whitelist()
	def create_test(self) -> "DriftTest":
		session = get_random_session_server().create_session()
		test = frappe.get_doc(
			{"doctype": "Drift Test", "definition": self.name, "session": session.name, "session_user": None}
		)
		test.insert(ignore_permissions=True)
		return test
