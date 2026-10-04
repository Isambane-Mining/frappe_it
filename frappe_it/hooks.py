app_name = "frappe_it"
app_title = "IT"
app_publisher = "buff0k"
app_description = "IT Management using Frappe and ERPNext"
app_email = "buff0k@gmail.com"
app_license = "mit"
app_home = "/desk/it"
app_logo_url = "/assets/frappe_it/images/is-logo.png"
required_apps = ["frappe/erpnext", "frappe/hrms"]
add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/frappe_it/images/is-logo.png",
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
]
# Asset Categories and Item Groups are not fixtures: Asset Categories need
# company-specific accounts and Item Groups need the root Item Group, which
# only exists after ERPNext's setup wizard. Both are created by frappe_it.setup
# once the site is ready, retried on every migrate until then.
after_install = [
	"frappe_it.setup.item_groups.ensure_item_groups",
	"frappe_it.setup.asset_categories.ensure_asset_categories",
]
after_migrate = [
	"frappe_it.setup.add_employee_doclinks.ensure_employee_links",
	"frappe_it.setup.add_asset_doclinks.ensure_asset_links",
	"frappe_it.setup.item_groups.ensure_item_groups",
	"frappe_it.setup.asset_categories.ensure_asset_categories",
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