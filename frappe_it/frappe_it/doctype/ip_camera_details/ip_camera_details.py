# Copyright (c) 2025, BuFf0k and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from frappe_it.frappe_it.utils import device_url_for


class IPCameraDetails(Document):
	def validate(self):
		self.ip_address = (self.ip_address or "").strip()
		self.camera_link = device_url_for(self.ip_address)
