import frappe

def check_app_permission():
    """Check if the user has permission to access the app (for showing it on the app screen)"""
    # Administrator always has access
    if frappe.session.user == "Administrator":
        return True

    # Check if the user has any of the required roles
    required_roles = ["System Manager", "IT Manager", "IT User"]
    user_roles = frappe.get_roles(frappe.session.user)

    # Grant access if the user has at least one of the required roles
    if any(role in user_roles for role in required_roles):
        return True

    return False


def device_url_for(ip_address, label="IP Address"):
	"""Validate an IPv4 address and return its http:// device URL."""
	import ipaddress

	from frappe import _

	ip_address = (ip_address or "").strip()
	try:
		ipaddress.IPv4Address(ip_address)
	except ValueError:
		frappe.throw(_("{0} '{1}' is not a valid IPv4 address.").format(_(label), ip_address))
	return f"http://{ip_address}"
