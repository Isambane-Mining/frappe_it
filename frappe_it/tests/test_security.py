# Copyright (c) 2026, buff0k and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from frappe_it.controllers.lookups import get_holder_details
from frappe_it.frappe_it.doctype.nvr_details.nvr_details import get_linked_cameras_html
from frappe_it.frappe_it.doctype.simcard_allocations.simcard_allocations import get_available_simcards
from frappe_it.setup.permissions import IT_PERMISSIONS, PTYPES, ensure_it_permissions
from frappe_it.tests.factories import make_asset, make_employee, make_location


class TestSimcardQuery(IntegrationTestCase):
	def test_injected_searchfield_is_rejected(self):
		with self.assertRaises(frappe.DataError):
			get_available_simcards("Asset", "", "name) or 1=1 -- ", 0, 20, {})

	def test_only_unallocated_simcards_are_offered(self):
		location = make_location("_Test IT Store")
		asset = make_asset("_T-IT-SIM-Q", location)
		frappe.db.set_value("Asset", asset, "asset_category", "Cellphone Simcards")

		names = [row[0] for row in get_available_simcards("Asset", "_T-IT-SIM-Q", "name", 0, 20, {})]

		self.assertIn(asset, names)


class TestPermissionCheckedLookups(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_holder_details_needs_select_permission(self):
		employee = make_employee("_T-IT-EMP-1")
		self.assertEqual(get_holder_details("Employee", employee)["name"], employee)

		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_holder_details("Employee", employee)

	def test_holder_details_rejects_other_doctypes(self):
		with self.assertRaises(frappe.ValidationError):
			get_holder_details("User", "Administrator")

	def test_camera_panel_needs_read_and_hides_credentials(self):
		location = make_location("_Test IT Store")
		nvr = frappe.get_doc(
			{
				"doctype": "NVR Details",
				"asset": make_asset("_T-IT-NVR-1", location),
				"ip_address": "10.0.0.10",
				"username": "admin",
				"password": "nvr-secret-pw",
				"location": "Server room",
				"serial": "NVR-1",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "IP Camera Details",
				"asset": make_asset("_T-IT-CAM-1", location),
				"ip_address": "10.0.0.11",
				"username": "camuser",
				"password": "cam-secret-pw",
				"location": "Gate",
				"serial": "CAM-1",
				"linked_to_nvr": nvr.name,
			}
		).insert(ignore_permissions=True)

		html = get_linked_cameras_html(nvr.name)
		self.assertIn("10.0.0.11", html)
		self.assertNotIn("cam-secret-pw", html)
		self.assertNotIn("camuser", html)

		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_linked_cameras_html(nvr.name)
		frappe.set_user("Administrator")

		# Stored encrypted, masked in the column (needs the migrated Password field)
		self.assertNotIn("secret", frappe.db.get_value("IP Camera Details", "_T-IT-CAM-1", "password"))


class TestDeviceValidation(IntegrationTestCase):
	def _camera(self, ip_address, asset):
		camera = frappe.get_doc(
			{
				"doctype": "IP Camera Details",
				"asset": make_asset(asset, make_location("_Test IT Store")),
				"ip_address": ip_address,
				"username": "u",
				"password": "p",
				"location": "Gate",
				"serial": asset,
				"linked_to_nvr": "_none_",
			}
		)
		camera.flags.ignore_links = True
		return camera.insert(ignore_permissions=True)

	def test_invalid_ip_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._camera("999.1.1.1", "_T-IT-CAM-2")

	def test_valid_ip_is_trimmed_and_sets_link(self):
		camera = self._camera(" 10.1.2.3 ", "_T-IT-CAM-3")
		self.assertEqual(camera.ip_address, "10.1.2.3")
		self.assertEqual(camera.camera_link, "http://10.1.2.3")


class TestITPermissions(IntegrationTestCase):
	def test_ensure_sets_exact_rights_and_keeps_other_roles(self):
		other_roles_before = frappe.db.count("Custom DocPerm", {"parent": "Employee", "role": ["not in", ["IT Manager", "IT User"]]})

		ensure_it_permissions()

		for doctype, roles in IT_PERMISSIONS.items():
			for role, rights in roles.items():
				row = frappe.db.get_value(
					"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, list(PTYPES), as_dict=True
				)
				self.assertIsNotNone(row, f"{doctype} / {role}")
				granted = {ptype for ptype in PTYPES if row[ptype]}
				self.assertEqual(granted, set(rights), f"{doctype} / {role}")

		employee_it = frappe.db.get_value("Custom DocPerm", {"parent": "Employee", "role": "IT User"}, ["select", "read"], as_dict=True)
		self.assertEqual((employee_it.select, employee_it.read), (1, 0))
		self.assertGreaterEqual(
			frappe.db.count("Custom DocPerm", {"parent": "Employee", "role": ["not in", ["IT Manager", "IT User"]]}),
			other_roles_before,
		)


class TestDevicePasswordReveal(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _user(self, email, roles):
		if not frappe.db.exists("User", email):
			user = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
			user.insert(ignore_permissions=True)
			user.add_roles(*roles)
		return email

	def test_it_manager_can_reveal_and_reveal_is_logged(self):
		from frappe_it.controllers.device_credentials import reveal_device_password

		location = make_location("_Test IT Store")
		nvr = frappe.get_doc(
			{
				"doctype": "NVR Details",
				"asset": make_asset("_T-IT-NVR-2", location),
				"ip_address": "10.0.0.20",
				"username": "admin",
				"password": "nvr-reveal-pw",
				"location": "Server room",
				"serial": "NVR-2",
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self._user("_test_it_manager@example.com", ["IT Manager"]))
		self.assertEqual(reveal_device_password("NVR Details", nvr.name), "nvr-reveal-pw")
		frappe.set_user("Administrator")
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "NVR Details", "reference_name": nvr.name, "content": ["like", "Password revealed by%"]},
			)
		)

		# No IT role at all, and IT User (which holds no rights on NVR Details)
		for email, roles in (("_test_not_it@example.com", ["Employee"]), ("_test_it_user@example.com", ["IT User"])):
			frappe.set_user(self._user(email, roles))
			with self.assertRaises(frappe.PermissionError):
				reveal_device_password("NVR Details", nvr.name)

	def test_other_doctypes_are_refused(self):
		from frappe_it.controllers.device_credentials import reveal_device_password

		with self.assertRaises(frappe.ValidationError):
			reveal_device_password("User", "Administrator")
