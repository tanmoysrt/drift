# Copyright (c) 2025, Tanmoy and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from drift.drift.doctype.drift_server.drift_server import DriftServer


class DriftServerNotAvailableException(Exception):
	pass


class DriftSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from drift.drift.doctype.drift_server.drift_server import DriftServer

		servers: DF.Table[DriftServer]
	# end: auto-generated types


def get_random_session_server() -> "DriftServer":
	# Chose a random server from the list of active servers
	# Try to find the server with lowest score = (active_sessions / memory_mb)

	DRIFT_SERVER = frappe.qb.DocType("Drift Server")
	query = (
		frappe.qb.from_(DRIFT_SERVER)
		.select(DRIFT_SERVER.name)
		.select((DRIFT_SERVER.active_sessions / DRIFT_SERVER.memory_mb).as_("score"))
		.where(DRIFT_SERVER.status != "Disabled")
		.orderby("score")
		.limit(1)
	)

	results = query.run(as_dict=True)
	if not results:
		frappe.throw(
			"No active Drift Server found. Please check the configured Drift Servers.",
			exc=DriftServerNotAvailableException,
		)

	return frappe.get_doc("Drift Server", results[0].name)


def sync_servers():
	servers = frappe.get_all("Drift Server", filters={"status": ("!=", "Disabled")}, pluck="name")
	for server in servers:
		frappe.enqueue_doc(
			"Drift Server",
			server,
			method="sync",
			timeout=300,
			deduplicate=True,
			job_id=f"sync_server||{server}",
			enqueue_after_commit=True,
		)


def sync_sessions():
	servers = frappe.get_all("Drift Server", filters={"status": ("!=", "Disabled")}, pluck="name")
	for server in servers:
		frappe.enqueue_doc(
			"Drift Server",
			server,
			method="sync_sessions",
			timeout=600,
			deduplicate=True,
			job_id=f"sync_sessions||{server}",
			enqueue_after_commit=True,
		)
