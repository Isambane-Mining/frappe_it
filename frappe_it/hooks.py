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
]
# The IT roles' permissions on core DocTypes (Asset, Employee, ...) are not a
# Custom DocPerm fixture: importing one onto a DocType without Custom DocPerm
# rows drops that DocType's standard permissions. frappe_it.setup.permissions
# applies them safely after every migrate instead.
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
	"frappe_it.setup.permissions.ensure_it_permissions",
]
# Only the first creation of a request / return emails the IT Managers.
doc_events = {
	"Asset Request": {
		"after_insert": "frappe_it.controllers.notifications.handle_doc_event_create",
	},
	"Asset Return": {
		"after_insert": "frappe_it.controllers.notifications.handle_doc_event_create",
	},
	# An allocated Asset must leave its Asset Allocation before it can be cancelled or deleted.
	"Asset": {
		"before_cancel": "frappe_it.controllers.asset_custody.block_if_allocated",
		"on_trash": "frappe_it.controllers.asset_custody.block_if_allocated",
	},
}