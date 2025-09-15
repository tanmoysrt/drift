# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

import contextlib
from collections.abc import Generator
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from playwright.sync_api import Browser, sync_playwright

if TYPE_CHECKING:
	from drift.drift.doctype.drift_server.drift_server import DriftServer


class DriftSessionConnectionError(Exception):
	pass


class DriftSession(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from drift.drift.doctype.drift_session_video.drift_session_video import DriftSessionVideo

		cdp_endpoint: DF.Data
		duration: DF.Duration | None
		ended_on: DF.Datetime | None
		purged_videos_from_server: DF.Check
		server: DF.Link
		session_id: DF.Data
		session_token: DF.Password
		started_on: DF.Datetime | None
		status: DF.Literal["Active", "Stopped"]
		video_download_status: DF.Literal["Draft", "Triggered", "Downloading", "Downloaded", "Deleted"]
		videos: DF.Table[DriftSessionVideo]
	# end: auto-generated types

	@property
	def server_doc(self) -> "DriftServer":
		return frappe.get_doc("Drift Server", self.server)

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Stopped":
			self.ended_on = frappe.utils.now_datetime()
			self.duration = int(frappe.utils.time_diff_in_seconds(self.ended_on, self.started_on))
			self.save()
			# Update the session ID if it has changed
			if self.video_download_status == "Draft":
				self.video_download_status = "Triggered"
				self.save()
				self.sync_video_ids_and_download()

	@contextlib.contextmanager
	def pw_browser(self) -> Generator[Browser, None, None]:
		pw = sync_playwright().start()
		browser = pw.chromium.connect_over_cdp(
			self.cdp_endpoint, headers={"Authorization": f"Bearer {self.get_password('session_token')}"}
		)
		try:
			yield browser
		except Exception as e:
			raise DriftSessionConnectionError from e
		finally:
			# don't close the browser, just stop playwright
			# as we will reuse the browser for the lifetime of the session
			with contextlib.suppress(Exception):
				pw.stop()

	@frappe.whitelist()
	def destroy_remote_session(self) -> bool:
		is_deleted = self.server_doc.destroy_session(self.session_id)
		if is_deleted:
			frappe.msgprint("Remote session destroyed. Status will be updated shortly.")
		else:
			frappe.msgprint("Failed to destroy remote session. Please try again.")
		return is_deleted

	def sync_video_ids_and_download(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			method="_sync_video_ids_and_download",
			timeout=600,
			deduplicate=True,
			job_id=f"sync_video_ids_and_download||{self.name}",
			enqueue_after_commit=True,
		)

	def _sync_video_ids_and_download(self):
		if self.video_download_status != "Triggered" or self.videos:
			return

		video_ids = self.server_doc.get_videos(self.session_id)
		if not video_ids:
			self.video_download_status = "Downloaded"
			self.save()
			return

		for id in video_ids:
			self.append("videos", {"id": id})

		self.video_download_status = "Downloading"
		self.save()

	def purge_downloaded_videos_from_remote(self):
		if self.purged_videos_from_server or self.video_download_status != "Downloaded":
			return

		if self.server_doc.delete_videos(session_id=self.session_id):
			frappe.db.set_value(self.doctype, self.name, "purged_videos_from_server", True)

	@frappe.whitelist()
	def delete_downloaded_videos(self):
		if self.video_download_status != "Downloaded":
			return
		for video in self.videos:
			if video.status == "Downloaded" and video.file:
				try:
					frappe.delete_doc("File", video.file, force=1)
				except Exception:
					pass
				video.file = None
				video.status = "Deleted"
		self.video_download_status = "Deleted"
		frappe.msgprint("Deleted downloaded videos")
		self.save()

	@frappe.whitelist()
	def get_recorded_video_urls(self) -> list[str]:
		if not self.videos:
			return []
		if self.status != "Stopped" or self.video_download_status != "Downloaded":
			return []
		return [video.file_url_path for video in self.videos if video.file and video.file_url_path]


def trigger_sync_video_ids_and_download():
	sessions = frappe.get_all(
		"Drift Session",
		filters={
			"status": "Stopped",
			"video_download_status": "Triggered",
			"ended_on": (
				">",
				frappe.utils.add_to_date(minutes=-2),
			),  # wait for at least 2 minutes after stopping to ensure videos has been written
			# TODO: need a better fix on agent side to ensure videos are ready to be downloaded instantly after stopping
		},
		pluck="name",
	)
	for session in sessions:
		try:
			frappe.get_doc("Drift Session", session).sync_video_ids_and_download()
			frappe.db.commit()
		except Exception:
			pass


def sync_video_download_status():
	sessions = frappe.get_all(
		"Drift Session",
		filters={"status": "Stopped", "video_download_status": "Downloading"},
		pluck="name",
	)
	for session in sessions:
		try:
			# Try to find sessions with `Pending` status
			all_downloaded = (
				frappe.db.count("Drift Session Video", {"parent": session, "status": "Pending"}) == 0
			)
			if all_downloaded:
				frappe.db.set_value("Drift Session", session, "video_download_status", "Downloaded")
				frappe.db.commit()
		except Exception:
			pass


def purge_downloaded_remote_videos():
	sessions = frappe.get_all(
		"Drift Session",
		filters={"purged_videos_from_server": False, "video_download_status": "Downloaded"},
		pluck="name",
	)
	for session in sessions:
		with contextlib.suppress(Exception):
			frappe.get_doc("Drift Session", session).purge_downloaded_videos_from_remote()
			frappe.db.commit()
