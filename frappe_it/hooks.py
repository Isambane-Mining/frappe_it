app_name = "frappe_it"
app_title = "Frappe IT"
app_publisher = "buff0k"
app_description = "IT Management using Frappe and ERPNext"
app_email = "buff0k@gmail.com"
app_license = "mit"
app_home = "/desk/it"
app_logo_url = "/assets/frappe_it/images/is-logo.svg"
required_apps = ["frappe/erpnext", "frappe/hrms"]
add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/frappe_it/images/is-logo.svg",
		"title": app_title,
		"route": app_home,
		"has_permission": "frappe_it.frappe_it.utils.check_app_permission",
	}
]
fixtures = [
	{"dt": "Role", "filters": [["name", "in", [
		"IT Manager",
		"IT User"
	]]]},
	{"dt": "Custom DocPerm", "filters": [["role", "in", [
		"IT Manager",
		"IT User"
	]]]},
	{"dt": "Asset Category", "filters": [["name", "in", [
		"Cellphone Simcards",
		"Handheld Radio",
		"IP Cameras",
		"NVRs",
		"Vehicle Mounted Radio",
		"Cellular Telephone",
		"Laptop Computer",
        "Computer Monitor"
	]]]},
	{"dt": "Item Group", "filters": [["name", "in", [
		"Cellphone Simcards",
		"Handheld Radio",
		"IP Cameras",
		"NVRs",
		"Vehicle Mounted Radio",
		"Cellular Telephone",
		"Laptop Computer"
	]]]}
]
after_migrate = [
	"frappe_it.setup.add_employee_doclinks.ensure_employee_links",
	"frappe_it.setup.add_asset_doclinks.ensure_asset_links"
]
doc_events = {
	"Asset Request": {
		"after_insert": "frappe_it.controllers.notifications.handle_doc_event_create",
		"on_update": "frappe_it.controllers.notifications.handle_doc_event_update",
		"on_submit": "frappe_it.controllers.notifications.handle_doc_event_submit",
	},
	"Asset Return": {
		"after_insert": "frappe_it.controllers.notifications.handle_doc_event_create",
		"on_update": "frappe_it.controllers.notifications.handle_doc_event_update",
		"on_submit": "frappe_it.controllers.notifications.handle_doc_event_submit",
	}
}