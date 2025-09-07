# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

import contextlib
from datetime import datetime
from typing import Literal

import frappe
import requests
from frappe.core.doctype.file.file import File
from frappe.model.document import Document

from drift.drift.doctype.drift_session.drift_session import DriftSession


class DriftServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active_sessions: DF.Int
		auth_token: DF.Password
		host: DF.Data
		memory_mb: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		scheme: DF.Literal["http", "https"]
		status: DF.Literal["Disabled", "Active", "Unreachable"]
	# end: auto-generated types

	def sync(self):
		success, data = self._send_request("GET", "/health")

		previous_status = self.status
		previous_active_sessions = self.active_sessions

		if success:
			self.status = "Active"
			self.active_sessions = data.get("sessions", 0)
		else:
			self.status = "Unreachable"

		if self.status != previous_status:
			frappe.db.set_value(self.doctype, self.name, "status", self.status, update_modified=False)

		if self.active_sessions != previous_active_sessions:
			frappe.db.set_value(
				self.doctype, self.name, "active_sessions", self.active_sessions, update_modified=False
			)

	def sync_sessions(self) -> dict:
		success, data = self._send_request("GET", "/sessions")
		if not success:
			frappe.log_error(f"Failed to sync sessions from server {self.host}")
			return

		current_active_session_ids = [s.get("session_id") for s in data]

		# Fetch active sessions on our system
		new_inactive_sessions = frappe.get_all(
			"Drift Session",
			filters={
				"server": self.name,
				"status": "Active",
				"session_id": ["not in", current_active_session_ids],
			},
			pluck="name",
		)

		for name in new_inactive_sessions:
			with contextlib.suppress(Exception):
				frappe.db.get_value("Drift Session", name, "status", for_update=True)
				doc = frappe.get_doc("Drift Session", name)
				doc.status = "Stopped"
				doc.save()

	def create_session(self) -> "DriftSession":
		"""
		Create a new session on this server

		returns
		- session_id: str
		- auth_token: str
		"""
		success, data = self._send_request("POST", "/sessions")

		if not success:
			frappe.throw("Failed to create browser session on the server")

		return frappe.get_doc(
			{
				"doctype": "Drift Session",
				"status": "Active",
				"server": self.name,
				"session_id": data.get("session_id"),
				"session_token": data.get("auth_token"),
				"cdp_endpoint": data.get("endpoint"),
				"started_on": datetime.fromtimestamp(data.get("created_on")),
			}
		).insert(ignore_permissions=True)

	def destroy_session(self, session_id: str) -> bool:
		# Destroy the session on this server
		success, _ = self._send_request("DELETE", f"/sessions/{session_id}", timeout=60)
		return success

	def is_session_active(self, session_id: str) -> bool:
		success, data = self._send_request("GET", f"/sessions/{session_id}")
		if not success:
			return False
		return data.get("status") == "Active"

	def get_videos(self, session_id: str) -> list[str]:
		success, data = self._send_request("GET", f"/sessions/{session_id}/videos")
		if not success or not data:
			return []
		return data

	def delete_videos(self, session_id: str) -> bool:
		success, _ = self._send_request("DELETE", f"/sessions/{session_id}/videos")
		return success

	def download_video(self, session_id: str, video_id: str) -> File:
		success, data = self._send_request("GET", f"/sessions/{session_id}/videos/{video_id}", is_json=False)
		if not success:
			frappe.throw("Failed to download video from the server")

		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": video_id,
				"content": data,
				"is_private": True,
			}
		).insert(ignore_permissions=True)
		return file

	def _send_request(
		self,
		method: Literal["GET", "POST", "PUT", "DELETE"],
		path: str,
		body: dict | None = None,
		timeout: int = 5,
		is_json: bool = True,
	) -> tuple[bool, dict | bytes]:
		if path and path[0] == "/":
			path = path[1:]

		# Make a request to the server
		res = requests.request(
			method=method,
			url=self._base_url + path,
			headers={"Authorization": f"Bearer {self.get_password('auth_token')}"},
			json=body or {},
			timeout=timeout,
		)

		success = res.status_code == 200
		response_Data = {}

		try:
			if is_json:
				response_Data = res.json()
			else:
				response_Data = res.content
		except Exception:
			success = False

		return success, response_Data

	@property
	def _base_url(self) -> str:
		return f"{self.scheme}://{self.host}/"
