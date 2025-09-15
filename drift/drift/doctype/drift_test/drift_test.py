# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING, Optional

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec

from drift.drift.utils import prepare_safe_exec_locals

if TYPE_CHECKING:
	from drift.drift.doctype.drift_session.drift_session import DriftSession
	from drift.drift.doctype.drift_test_step.drift_test_step import DriftTestStep
	from drift.drift.doctype.drift_test_step_definition.drift_test_step_definition import (
		DriftTestStepDefinition,
	)


class DriftTest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from drift.drift.doctype.drift_test_document.drift_test_document import DriftTestDocument
		from drift.drift.doctype.drift_test_step.drift_test_step import DriftTestStep

		definition: DF.Link
		documents: DF.Table[DriftTestDocument]
		session: DF.Link | None
		session_user: DF.Data | None
		session_user_sid: DF.Data | None
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Cancelled", "Stopped"]
		steps: DF.Table[DriftTestStep]
		variables: DF.SmallText
	# end: auto-generated types

	@property
	def variables_dict(self):
		if not self.variables:
			return frappe._dict()
		try:
			return frappe._dict(frappe.json.loads(self.variables))
		except json.JSONDecodeError:
			return frappe._dict()

	@property
	def current_running_step(self) -> Optional["DriftTestStep"]:
		for step in self.steps:
			if step.status == "Running":
				return step
		return None

	@property
	def next_step(self) -> Optional["DriftTestStep"]:
		for step in self.steps:
			if step.status == "Pending":
				return step
		return None

	@property
	def session_doc(self) -> Optional["DriftSession"]:
		if self.session:
			return frappe.get_cached_doc("Drift Session", self.session)
		return None

	def on_update(self):
		if self.has_value_changed("status") and self.status in ["Success", "Failure", "Stopped", "Cancelled"]:
			session = self.session_doc
			if session and session.status == "Active":
				session.destroy_remote_session()

	def execute_step(self, step_name: str):
		step = self._get_step(step_name)
		step_definition: DriftTestStepDefinition = frappe.get_cached_doc(
			"Drift Test Step Definition", step.step
		)
		code = step_definition.code.strip()
		code = code.replace("{{sid}}", self.session_user_sid or "")

		with self.session_doc.pw_browser() as browser:
			safe_exec_locals = prepare_safe_exec_locals(self.variables_dict)
			try:
				frappe.msgprint(f"Code -<br><br>{code}")
				if not step.started_at:
					step.started_at = frappe.utils.now_datetime()

				step.last_attempted_at = frappe.utils.now_datetime()

				# Prepare Playwright context and page
				pw_context = browser.contexts[0] if browser.contexts else browser.new_context()
				pw_page = pw_context.pages[0] if pw_context.pages else pw_context.new_page()
				safe_exec_locals.update({"pw_ctx": pw_context, "pw_page": pw_page, "doc": self})

				# Execute the code
				safe_exec(code, _locals=safe_exec_locals)

				# Extract variables and store those
				self.variables = json.dumps(safe_exec_locals.get("variables", {}), indent=2)
				step.no_of_attempts = (step.no_of_attempts or 0) + 1

				if not step_definition.wait_for_completion:
					step.status = "Success"
				else:
					result = safe_exec_locals.get("result", (True, False))
					if (isinstance(result, tuple) or isinstance(result, list)) and len(result) == 2:
						if result[0]:
							step.status = "Success"
						elif result[1]:
							step.status = "Failure"
							step.error = "Step failed as per the 'result' variable"
						else:
							# Check for timeout
							duration = int(
								frappe.utils.time_diff_in_seconds(
									frappe.utils.now_datetime(), step.started_at
								)
							)
							if duration > step_definition.timeout_seconds:
								step.status = "Failure"
								step.error = "Step timed out after {} seconds".format(
									step_definition.timeout_seconds
								)
							else:
								step.status = "Running"
			except Exception as e:
				import traceback

				step.status = "Failure"
				step.error = str(e)
				step.traceback = traceback.format_exc()

			finally:
				if step.status in ("Success", "Failure"):
					if not step.started_at:
						step.started_at = frappe.utils.now_datetime()
					if not step.last_attempted_at:
						step.last_attempted_at = frappe.utils.now_datetime()

					step.ended_at = frappe.utils.now_datetime()
					step.duration = int(frappe.utils.time_diff_in_seconds(step.ended_at, step.started_at))

		if step.status == "Failure":
			self.finish(save=True)
		else:
			# Check if session user or sid has been updated in variables
			variables = self.variables_dict
			if (
				"session_user" in variables
				and "session_user_sid" in variables
				and variables.get("session_user")
				and variables.get("session_user_sid")
			):
				self.session_user = variables.get("session_user")
				self.session_user_sid = variables.get("session_user_sid")

			# Save the test and move to next step
			self.save(ignore_version=True)
			self.next()

	@frappe.whitelist()
	def next(self):
		if self.status != "Running" and self.status not in ("Success", "Failure", "Stopped", "Cancelled"):
			self.status = "Running"
			self.save(ignore_version=True)

		if frappe.db.get_value("Drift Session", self.session, "status") != "Active":
			self.status = "Stopped"
			self.save(ignore_version=True)

		next_step_to_run = None

		current_running_step = self.current_running_step
		if current_running_step:
			next_step_to_run = current_running_step
		elif self.next_step:
			next_step_to_run = self.next_step

		if not next_step_to_run:
			# We've executed everything
			self.finish()
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"execute_step",
			step_name=next_step_to_run.name,
			enqueue_after_commit=True,
			deduplicate=frappe.db.get_value(
				"Drift Test Step Definition", next_step_to_run.step, "wait_for_completion"
			)
			is False,  # Don't deduplicate if wait_for_completion is True
			job_id=f"drift_test||{self.name}||{next_step_to_run.name}",
		)

	def _get_step(self, step_name: str) -> "DriftTestStep":
		for step in self.steps:
			if step.name == step_name:
				return step
		frappe.throw(f"Step {step_name} not found in test {self.name}")

	def finish(self, save: bool = True):
		if self.status in ("Success", "Failure", "Stopped", "Cancelled"):
			return
		if any(step.status == "Failure" for step in self.steps):
			self.status = "Failure"
		else:
			self.status = "Success"

		if save:
			self.save(ignore_version=True)
