# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

# import frappe
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from drift.drift.doctype.drift_server.drift_server import DriftServer


class DriftSessionVideo(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		file: DF.Link | None
		file_url_path: DF.Data | None
		id: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal["Pending", "Downloaded", "Download Failed", "Deleted"]
	# end: auto-generated types

	def download(self):
		if self.status == "Downloaded":
			return

		server: DriftServer = frappe.get_cached_doc(
			"Drift Server", frappe.get_value("Drift Session", self.parent, "server")
		)

		try:
			file = server.download_video(
				frappe.get_value("Drift Session", self.parent, "session_id"), self.id
			)
			self.file = file.name
			self.status = "Downloaded"
		except Exception as e:
			self.status = "Download Failed"
			frappe.log_error(f"Failed to download video {self.id} for session {self.parent}: {e}")
		finally:
			self.save()


def download_session_videos():
	session_videos = frappe.get_all("Drift Session Video", filters={"status": "Pending"}, pluck="name")
	for video in session_videos:
		frappe.enqueue_doc(
			"Drift Session Video",
			video,
			method="download",
			queue="long",
			timeout=600,
			deduplicate=True,
			job_id=f"download_drift_session_video||{video}",
			enqueue_after_commit=True,
		)
