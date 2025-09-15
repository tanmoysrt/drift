# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


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
		steps: DF.Table[DriftTestStep]
		variables: DF.SmallText
	# end: auto-generated types

	def before_insert(self):
		if not self.session:
			self.session_user = self.session_doc.get_user()
