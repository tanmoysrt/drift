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
		user_key: DF.Data
	# end: auto-generated types

	def validate(self):
		if self.interval_minutes is not None and self.interval_minutes < 2:
			frappe.throw("Interval Minutes cannot be less than 2 minutes")

		if self.interval_minutes and not self.next_execution_on:
			self.next_execution_on = frappe.utils.add_to_date(None, minutes=self.interval_minutes)

		if not self.steps:
			frappe.throw("Please add at least one step")

	@frappe.whitelist()
	def create_test(self) -> "DriftTest":
		session = get_random_session_server().create_session()
		test = frappe.get_doc(
			{
				"doctype": "Drift Test",
				"definition": self.name,
				"session": session.name,
				"session_user": None,
				"variables": frappe.db.get_value(
					"Drift Test Setup", self.test_setup, "default_local_variables"
				),
				"steps": [],
			}
		)
		for step in self.steps:
			test.append(
				"steps",
				{
					"step": step.name,
					"status": "Pending",
				},
			)
		test.insert(ignore_permissions=True)
		test.next()
		self.last_executed_on = frappe.utils.now_datetime()
		self.next_execution_on = frappe.utils.add_to_date(
			self.last_executed_on, minutes=self.interval_minutes
		)
		self.save(ignore_permissions=True, ignore_version=True)
		frappe.msgprint(f"Test <a href='/app/drift-test/{test.name}'>{test.name}</a> created successfully")
		return test


def auto_trigger_tests():
	for definition in frappe.get_all(
		"Drift Test Definition",
		filters={"enabled": 1, "next_execution_on": ["<=", frappe.utils.now_datetime()]},
		pluck="name",
	):
		try:
			test = frappe.get_doc("Drift Test Definition", definition).create_test()
			test.next()
			frappe.db.commit()
		except Exception as e:
			frappe.log_error("Failed to auto trigger test: " + definition, e)
			continue
